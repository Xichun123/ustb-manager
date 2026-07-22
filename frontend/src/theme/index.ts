import type { ThemeConfig } from 'antd'
import { theme as antdTheme } from 'antd'

// USTB 品牌色
export const BRAND_COLOR = '#003366'
export const BRAND_COLOR_LIGHT = '#0b5cad'

export const FONT_FAMILY = `-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', 'Helvetica Neue', Helvetica, Arial, sans-serif`

// 亮色主题
export const lightTheme: ThemeConfig = {
  algorithm: antdTheme.defaultAlgorithm,
  token: {
    colorPrimary: BRAND_COLOR_LIGHT,
    colorInfo: BRAND_COLOR_LIGHT,
    colorLink: BRAND_COLOR_LIGHT,
    colorBgLayout: '#f5f7fa',
    colorBgContainer: '#ffffff',
    borderRadius: 10,
    fontFamily: FONT_FAMILY,
  },
  components: {
    Layout: {
      headerBg: 'rgba(255, 255, 255, 0.8)',
      headerHeight: 60,
      siderBg: '#ffffff',
    },
    Menu: {
      itemBg: 'transparent',
      itemSelectedBg: 'rgba(11, 92, 173, 0.08)',
      itemSelectedColor: BRAND_COLOR_LIGHT,
      itemBorderRadius: 8,
      itemMarginInline: 8,
    },
    Card: {
      borderRadiusLG: 14,
      boxShadowTertiary: '0 1px 2px rgba(0, 0, 0, 0.03), 0 4px 16px rgba(0, 0, 0, 0.04)',
    },
    Table: {
      headerBg: '#fafbfc',
      headerSplitColor: 'transparent',
    },
    Tabs: {
      horizontalMargin: '0 0 16px 0',
    },
  },
}

// 暗色主题
export const darkTheme: ThemeConfig = {
  algorithm: antdTheme.darkAlgorithm,
  token: {
    colorPrimary: '#3a7fd4',
    colorInfo: '#3a7fd4',
    colorLink: '#5c9ce6',
    colorBgLayout: '#0f1419',
    colorBgContainer: '#1a222c',
    borderRadius: 10,
    fontFamily: FONT_FAMILY,
  },
  components: {
    Layout: {
      headerBg: 'rgba(26, 34, 44, 0.8)',
      headerHeight: 60,
      siderBg: '#141b24',
    },
    Menu: {
      itemBg: 'transparent',
      itemSelectedBg: 'rgba(58, 127, 212, 0.15)',
      itemSelectedColor: '#5c9ce6',
      itemBorderRadius: 8,
      itemMarginInline: 8,
    },
    Card: {
      borderRadiusLG: 14,
    },
    Table: {
      headerBg: '#141b24',
      headerSplitColor: 'transparent',
    },
    Tabs: {
      horizontalMargin: '0 0 16px 0',
    },
  },
}
