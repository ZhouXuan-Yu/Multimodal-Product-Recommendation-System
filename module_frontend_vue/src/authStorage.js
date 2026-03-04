// 轻量本地存储封装：负责保存 / 恢复当前登录用户
const STORAGE_KEY = 'jin_auth_user'

export function loadAuthUser() {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw)
    // 基础字段校验，避免历史脏数据
    if (!parsed || typeof parsed !== 'object' || !parsed.email) return null
    return parsed
  } catch {
    return null
  }
}

export function saveAuthUser(user) {
  try {
    if (!user) {
      window.localStorage.removeItem(STORAGE_KEY)
      return
    }
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(user))
  } catch {
    // 静默失败：不影响主流程
  }
}

export function clearAuthUser() {
  try {
    window.localStorage.removeItem(STORAGE_KEY)
  } catch {
    // ignore
  }
}

