// 客户端本地稳定的自增 id，用于 v-for 的 :key。
// 通过 Object.defineProperty 定义成不可枚举属性，JSON.stringify / 序列化不携带，
// 避免 `_uid` 泄漏进提交 payload 或被后端 json.dumps 落地 DB。
let seq = 0

export const nextUid = () => ++seq

export const stampUid = (item) => {
  Object.defineProperty(item, '_uid', {
    value: nextUid(),
    enumerable: false,
    writable: true,
    configurable: true
  })
  return item
}
