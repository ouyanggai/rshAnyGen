/**
 * LocalStorage 封装 - 带自动错误恢复
 */
class Storage {
  constructor() {
    this.prefix = 'rshanygen_';
  }

  // 生成带前缀的键名
  _getKey(key) {
    return `${this.prefix}${key}`;
  }

  get(key, defaultValue = null) {
    try {
      const item = localStorage.getItem(this._getKey(key));
      if (!item) {
        return defaultValue;
      }

      // 尝试解析 JSON
      try {
        return JSON.parse(item);
      } catch (parseError) {
        // 解析失败，清除无效数据并返回默认值
        console.warn(`Storage: Invalid JSON for key "${key}", clearing and returning default`);
        localStorage.removeItem(this._getKey(key));
        return defaultValue;
      }
    } catch (error) {
      console.error('Storage get error:', error);
      return defaultValue;
    }
  }

  set(key, value) {
    try {
      localStorage.setItem(this._getKey(key), JSON.stringify(value));
    } catch (error) {
      console.error('Storage set error:', error);
      // 可能是配额超限，尝试清理旧数据
      this.cleanup();
    }
  }

  remove(key) {
    try {
      localStorage.removeItem(this._getKey(key));
    } catch (error) {
      console.error('Storage remove error:', error);
    }
  }

  clear() {
    try {
      // 只清除本应用的数据
      const keys = Object.keys(localStorage);
      keys.forEach(key => {
        if (key.startsWith(this.prefix)) {
          localStorage.removeItem(key);
        }
      });
    } catch (error) {
      console.error('Storage clear error:', error);
    }
  }

  // 清理可能损坏的数据
  cleanup() {
    try {
      const keys = Object.keys(localStorage);
      keys.forEach(key => {
        if (key.startsWith(this.prefix)) {
          try {
            const item = localStorage.getItem(key);
            if (item) {
              JSON.parse(item); // 验证 JSON 是否有效
            }
          } catch {
            // 无效数据，删除
            localStorage.removeItem(key);
          }
        }
      });
    } catch (error) {
      console.error('Storage cleanup error:', error);
    }
  }

  // 获取存储大小（近似值）
  getSize() {
    try {
      let total = 0;
      const keys = Object.keys(localStorage);
      keys.forEach(key => {
        if (key.startsWith(this.prefix)) {
          const item = localStorage.getItem(key);
          if (item) {
            total += key.length + item.length;
          }
        }
      });
      return total;
    } catch {
      return 0;
    }
  }
}

export const storage = new Storage();
