// frontend/src/utils/__tests__/testid.spec.ts
import { describe, it, expect } from 'vitest'
import { slug } from '../testid'

describe('slug', () => {
  it('保留中文字符', () => {
    expect(slug('僧侣')).toBe('僧侣')
  })
  it('斜杠/空格/括号转连字符', () => {
    expect(slug('Front/Left')).toBe('front-left')
    expect(slug('男性 (M)')).toBe('男性-m')
  })
  it('小写英文字母', () => {
    expect(slug('Warrior')).toBe('warrior')
  })
  it('多个连续分隔符压缩为单个连字符', () => {
    expect(slug('a   b///c')).toBe('a-b-c')
  })
  it('去首尾连字符', () => {
    expect(slug('--abc--')).toBe('abc')
  })
  it('空字符串返回空', () => {
    expect(slug('')).toBe('')
  })
})
