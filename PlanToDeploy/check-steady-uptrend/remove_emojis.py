# -*- coding: utf-8 -*-
"""
批量移除Python文件中的emoji，替换为文本标记
"""
import re
from pathlib import Path

# Emoji到文本的映射
EMOJI_MAP = {
    '[OK]': '[OK]',
    '[ERROR]': '[ERROR]',
    '[DIR]': '[DIR]',
    '[CHART]': '[CHART]',
    '[UP]': '[UP]',
    '[GRID]': '[GRID]',
    '[MYSTIC]': '[MYSTIC]',
    '[START]': '[START]',
    '[SKIP]': '[SKIP]',
    '[STAR]': '[STAR]',
    '[STAR]': '[STAR]',
}

def remove_emojis_from_file(file_path):
    """从文件中移除emoji"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # 替换已知的emoji
        for emoji, text in EMOJI_MAP.items():
            content = content.replace(emoji, text)
        
        # 如果内容有变化，写回文件
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        return False
    except Exception as e:
        print(f"处理文件失败 {file_path}: {e}")
        return False

def main():
    base_dir = Path(r"C:\Users\Administrator\Desktop\Park\stocks-fliter\check-steady-uptrend")
    
    # 查找所有Python文件
    py_files = list(base_dir.rglob("*.py"))
    
    print(f"找到 {len(py_files)} 个Python文件")
    
    modified_count = 0
    for py_file in py_files:
        if remove_emojis_from_file(py_file):
            print(f"  [OK] {py_file.relative_to(base_dir)}")
            modified_count += 1
    
    print(f"\n完成！修改了 {modified_count} 个文件")

if __name__ == "__main__":
    main()

