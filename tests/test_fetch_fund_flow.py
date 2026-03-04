#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests for fetch_fund_flow.py

Test-Driven Development:
1. Tests are written BEFORE implementation
2. Run tests - they should FAIL initially
3. Implement code to make tests PASS
4. Refactor while keeping tests green
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "get-data"))

# Import after path setup
import fetch_fund_flow as fff


class TestFetchFundFlowData(unittest.TestCase):
    """Test fetch_fund_flow_data function with mocked AkShare"""

    @patch('fetch_fund_flow.ak.stock_individual_fund_flow')
    def test_successful_fetch_returns_dataframe(self, mock_ak_func):
        """成功获取数据时返回 DataFrame"""
        # Arrange
        mock_df = pd.DataFrame({
            '日期': ['2026-02-27'],
            '收盘价': [10.0],
            '涨跌幅': [1.0],
            '主力净流入-净额': [1000000.0],
            '主力净流入-净占比': [5.0],
            '超大单净流入-净额': [500000.0],
            '超大单净流入-净占比': [2.5],
            '大单净流入-净额': [500000.0],
            '大单净流入-净占比': [2.5],
            '中单净流入-净额': [-300000.0],
            '中单净流入-净占比': [-1.5],
            '小单净流入-净额': [-700000.0],
            '小单净流入-净占比': [-3.5],
        })
        mock_ak_func.return_value = mock_df

        # Act
        result = fff.fetch_fund_flow_data('600121')

        # Assert
        self.assertIsNotNone(result)
        self.assertIsInstance(result, pd.DataFrame)
        self.assertIn('date', result.columns)
        self.assertIn('code', result.columns)
        self.assertEqual(result['code'].iloc[0], '600121')

    def test_module_has_browser_headers_config(self):
        """模块应该配置了浏览器请求头来避免被识别为爬虫"""
        # 检查模块是否定义了浏览器请求头
        self.assertTrue(hasattr(fff, 'BROWSER_HEADERS'))
        headers = fff.BROWSER_HEADERS
        self.assertIn('User-Agent', headers)
        # User-Agent 应该包含浏览器标识
        ua = headers.get('User-Agent', '')
        self.assertTrue(
            'Mozilla' in ua or 'Chrome' in ua or 'Safari' in ua,
            f"User-Agent should look like browser, got: {ua}"
        )

    @patch('fetch_fund_flow.ak.stock_individual_fund_flow')
    def test_retry_on_failure(self, mock_ak_func):
        """失败时应该重试指定次数"""
        # Arrange - 前2次失败，第3次成功
        mock_ak_func.side_effect = [
            Exception("Connection error"),
            Exception("Connection error"),
            pd.DataFrame({
                '日期': ['2026-02-27'],
                '主力净流入-净额': [1000000.0],
            })
        ]

        # Act
        result = fff.fetch_fund_flow_data('600121', max_retries=3)

        # Assert
        self.assertIsNotNone(result)
        self.assertEqual(mock_ak_func.call_count, 3)

    @patch('fetch_fund_flow.ak.stock_individual_fund_flow')
    def test_return_none_after_max_retries(self, mock_ak_func):
        """超过最大重试次数后返回 None"""
        # Arrange - 总是失败
        mock_ak_func.side_effect = Exception("Connection error")

        # Act
        result = fff.fetch_fund_flow_data('600121', max_retries=2)

        # Assert
        self.assertIsNone(result)
        self.assertEqual(mock_ak_func.call_count, 2)

    @patch('fetch_fund_flow.ak.stock_individual_fund_flow')
    def test_sh_market_for_6xxx_codes(self, mock_ak_func):
        """6开头的代码应该使用 sh 市场"""
        mock_ak_func.return_value = pd.DataFrame({'日期': ['2026-02-27'], '主力净流入-净额': [100]})

        fff.fetch_fund_flow_data('600519')

        args = mock_ak_func.call_args
        self.assertEqual(args[1]['market'], 'sh')

    @patch('fetch_fund_flow.ak.stock_individual_fund_flow')
    def test_sz_market_for_0xxx_and_3xxx_codes(self, mock_ak_func):
        """0和3开头的代码应该使用 sz 市场"""
        mock_ak_func.return_value = pd.DataFrame({'日期': ['2026-02-27'], '主力净流入-净额': [100]})

        fff.fetch_fund_flow_data('000001')
        args = mock_ak_func.call_args
        self.assertEqual(args[1]['market'], 'sz')

        fff.fetch_fund_flow_data('300001')
        args = mock_ak_func.call_args
        self.assertEqual(args[1]['market'], 'sz')

    @patch('fetch_fund_flow.ak.stock_individual_fund_flow')
    def test_empty_dataframe_returns_none(self, mock_ak_func):
        """空数据应该返回 None"""
        mock_ak_func.return_value = pd.DataFrame()

        result = fff.fetch_fund_flow_data('600121')

        self.assertIsNone(result)


class TestGetMarket(unittest.TestCase):
    """Test get_market helper function"""

    def test_sh_for_6xxx_codes(self):
        """6开头返回 sh"""
        self.assertEqual(fff.get_market('600519'), 'sh')
        self.assertEqual(fff.get_market('688888'), 'sh')

    def test_sz_for_0xxx_codes(self):
        """0开头返回 sz"""
        self.assertEqual(fff.get_market('000001'), 'sz')
        self.assertEqual(fff.get_market('002594'), 'sz')

    def test_sz_for_3xxx_codes(self):
        """3开头返回 sz"""
        self.assertEqual(fff.get_market('300001'), 'sz')
        self.assertEqual(fff.get_market('300750'), 'sz')


class TestMergeData(unittest.TestCase):
    """Test merge_data function"""

    def test_merge_with_existing_data(self):
        """合并新旧数据应该去重并保留最新"""
        existing = pd.DataFrame({
            'date': ['2026-02-25', '2026-02-26'],
            'code': ['600121', '600121'],
            'main_force_net': [100.0, 200.0]
        })
        new = pd.DataFrame({
            'date': ['2026-02-26', '2026-02-27'],
            'code': ['600121', '600121'],
            'main_force_net': [250.0, 300.0]
        })

        result = fff.merge_data(existing, new)

        # 应该有 3 条记录（去重后保留新数据中的 2026-02-26）
        self.assertEqual(len(result), 3)
        # 2026-02-26 应该使用新数据 (250.0)
        feb_26_row = result[result['date'] == '2026-02-26']
        self.assertEqual(feb_26_row['main_force_net'].iloc[0], 250.0)

    def test_merge_with_none_existing(self):
        """existing 为 None 时返回 new"""
        new = pd.DataFrame({'date': ['2026-02-27'], 'code': ['600121']})

        result = fff.merge_data(None, new)

        pd.testing.assert_frame_equal(result, new)


class TestColumnMapping(unittest.TestCase):
    """Test column naming and mapping"""

    def test_all_required_columns_present(self):
        """确保所有需要的列都在 COLUMN_MAPPING 中"""
        required_source_columns = [
            '日期', '收盘价', '涨跌幅',
            '主力净流入-净额', '主力净流入-净占比',
            '超大单净流入-净额', '超大单净流入-净占比',
            '大单净流入-净额', '大单净流入-净占比',
            '中单净流入-净额', '中单净流入-净占比',
            '小单净流入-净额', '小单净流入-净占比',
        ]

        for col in required_source_columns:
            self.assertIn(col, fff.COLUMN_MAPPING)


if __name__ == '__main__':
    unittest.main()
