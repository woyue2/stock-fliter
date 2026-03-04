# -*- coding: utf-8 -*-
"""
Playwright 测试脚本 - 检查 HTML 报告

功能：
1. 打开 HTML 报告
2. 检查左侧导航栏显示的策略数量
3. 检查 localStorage 保存的勾选股票功能
4. 检查备注文本框功能
"""

from pathlib import Path
from playwright.sync_api import sync_playwright
import json
import os


def find_latest_report():
    """查找最新的报告文件"""
    output_dir = Path(__file__).parent / "output"
    
    if not output_dir.exists():
        return None
    
    # 查找所有带时间戳的目录
    date_dirs = sorted([d for d in output_dir.iterdir() if d.is_dir()], reverse=True)
    
    for date_dir in date_dirs:
        # 查找 summary.html 文件
        summary_files = list(date_dir.glob("summary*.html"))
        if summary_files:
            return summary_files[0]  # 返回最新的
    
    return None


def test_report():
    """测试 HTML 报告"""
    report_path = find_latest_report()
    
    if not report_path:
        print("❌ 未找到报告文件")
        print("请先运行: python check-new-indicators/main.py")
        return
    
    file_url = f"file:///{report_path}"
    print(f"📄 打开报告: {report_path}")
    print(f"📄 URL: {file_url}")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        
        # 打开报告
        page.goto(file_url)
        page.wait_for_load_state("networkidle")
        
        print("\n" + "="*60)
        print("🧪 HTML 报告测试开始")
        print("="*60)
        
        # 1. 检查左侧导航栏
        print("\n📊 1. 检查左侧导航栏...")
        nav_items = page.locator(".nav-item").all()
        print(f"   找到 {len(nav_items)} 个策略项")
        
        for item in nav_items[:5]:  # 只显示前5个
            name = item.locator(".strategy-name").inner_text()
            count = item.locator(".strategy-count").inner_text()
            print(f"   - {name}: {count} 只股票")
        
        if len(nav_items) > 5:
            print(f"   ... 还有 {len(nav_items) - 5} 个策略")
        
        # 2. 检查已选股票区域
        print("\n💾 2. 检查已选股票区域...")
        selected_container = page.locator("#selectedList")
        if selected_container.count() > 0:
            selected_text = selected_container.inner_text()
            print(f"   ✓ 已选股票区域存在: {selected_text[:50] if selected_text.strip() else '空'}")
        else:
            print("   ❌ 未找到已选股票区域")
        
        # 3. 检查备注输入框
        print("\n📝 3. 检查备注功能...")
        notes_input = page.locator("#notesInput")
        if notes_input.count() > 0:
            print("   ✓ 备注输入框存在")
            
            # 测试保存备注
            test_note = "测试备注 - " + "这是一个测试"
            notes_input.fill(test_note)
            page.evaluate("document.activeElement.blur()")
            
            saved_note = page.evaluate("localStorage.getItem('report_notes')")
            print(f"   ✓ 备注保存测试: {saved_note == test_note}")
        else:
            print("   ❌ 未找到备注输入框")
        
        # 4. 进入详情页测试勾选功能
        print("\n✅ 4. 测试详情页勾选功能...")
        
        # 点击第一个策略
        first_item = page.locator(".nav-item:not(.disabled)").first
        if first_item.count() > 0:
            first_item.click()
            page.wait_for_timeout(500)
            
            # 切换到 iframe 页面
            page.wait_for_selector("iframe")
            
            # 获取 iframe
            iframe = page.locator("iframe").first
            iframe_page = iframe.content_frame
            
            if iframe_page:
                # 查找勾选框
                checkbox = iframe_page.locator('input[type="checkbox"]').first
                if checkbox.count() > 0:
                    # 获取股票代码
                    stock_code = ""
                    try:
                        row = checkbox.locator("..")
                        stock_code = row.locator("td").first.inner_text()
                    except:
                        pass
                    
                    # 勾选
                    checkbox.check()
                    print(f"   ✓ 勾选股票: {stock_code}")
                    
                    # 检查是否通知父窗口
                    selected_list = page.locator("#selectedList")
                    selected_text = selected_list.inner_text()
                    print(f"   ✓ 父窗口同步: {stock_code in selected_text if stock_code else '未知'}")
                else:
                    print("   ⚠️  未找到勾选框")
            else:
                print("   ⚠️  无法访问 iframe 内容")
        
        # 5. 截图
        print("\n📸 5. 保存测试截图...")
        screenshot_path = Path(__file__).parent / "output" / "test_screenshot.png"
        page.screenshot(path=str(screenshot_path), full_page=True)
        print(f"   截图已保存: {screenshot_path}")
        
        print("\n" + "="*60)
        print("✅ 测试完成")
        print("="*60)
        
        browser.close()


def test_localstorage_api():
    """测试 localStorage API 功能"""
    print("\n" + "="*60)
    print("🧪 localStorage API 测试")
    print("="*60)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # 打开空白页测试 localStorage
        page.goto("about:blank")
        
        # 测试保存股票列表
        test_stocks = json.dumps(["600000", "600004", "600006"])
        page.evaluate(f"localStorage.setItem('selected_stocks', '{test_stocks}')")
        
        result = page.evaluate("localStorage.getItem('selected_stocks')")
        print(f"\n💾 保存股票: {result}")
        assert result == test_stocks, "股票保存失败"
        print("   ✓ 股票保存/读取正常")
        
        # 测试保存备注
        test_note = "测试备注内容"
        page.evaluate(f"localStorage.setItem('report_notes', '{test_note}')")
        
        result = page.evaluate("localStorage.getItem('report_notes')")
        print(f"\n📝 保存备注: {result}")
        assert result == test_note, "备注保存失败"
        print("   ✓ 备注保存/读取正常")
        
        # 测试删除
        page.evaluate("localStorage.removeItem('selected_stocks')")
        result = page.evaluate("localStorage.getItem('selected_stocks')")
        assert result is None, "删除失败"
        print("\n🗑️  删除功能正常")
        
        print("\n" + "="*60)
        print("✅ localStorage API 测试通过")
        print("="*60)
        
        browser.close()


if __name__ == "__main__":
    import sys
    
    # 切换到脚本所在目录，确保路径正确
    os.chdir(Path(__file__).parent)
    
    if len(sys.argv) > 1 and sys.argv[1] == "--api":
        test_localstorage_api()
    else:
        test_report()
