/**
 * 移动端常量组合式函数
 * 提供统一的常量访问方式
 */

import {
  ButtonTypes,
  ButtonSizes,
  TagTypes,
  FormSizes,
  ButtonText,
  StatusText,
  MessageText,
  PageTitle,
  FormLabel,
  ThemeOptions,
  LanguageOptions,
  QuickActions,
  BottomNavItems,
  Colors,
  type ButtonType,
  type ButtonSize,
  type TagType,
  type FormSize,
} from '../constants'

export function useMobileConstants() {
  return {
    // 类型常量
    ButtonTypes,
    ButtonSizes,
    TagTypes,
    FormSizes,

    // 文字常量
    ButtonText,
    StatusText,
    MessageText,
    PageTitle,
    FormLabel,

    // 选项常量
    ThemeOptions,
    LanguageOptions,
    QuickActions,
    BottomNavItems,

    // 颜色常量
    Colors,
  }
}

// 单独导出便捷函数
export function useButtonText() {
  return ButtonText
}

export function useStatusText() {
  return StatusText
}

export function useMessageText() {
  return MessageText
}

export function usePageTitle() {
  return PageTitle
}

export function useFormLabel() {
  return FormLabel
}

// 导出类型
export type { ButtonType, ButtonSize, TagType, FormSize }
