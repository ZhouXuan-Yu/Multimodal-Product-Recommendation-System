// 中文展示辅助：把后端/数据集中常见的英文类别、字段名、商品短语做“稳定映射”
// 说明：
// - 这里只做“展示层”的本地化，不影响后端检索/推荐逻辑
// - 不是完整机器翻译：对电商 Demo 常见词/短语做覆盖，剩余英文保持原样

export const CATEGORY_ZH_MAP = {
  electronics: '数码电子',
  jewelery: '珠宝配饰',
  "men's clothing": '男装',
  "women's clothing": '女装',
  sports: '运动户外',
  unknown: '未知',
}

export function formatCategoryZh(category) {
  if (!category) return '-'
  return CATEGORY_ZH_MAP[category] || category
}

const normalizeSpaces = (s) => (typeof s === 'string' ? s.replace(/\s+/g, ' ').trim() : s)

// 常见电商商品名短语（偏服饰/配饰/数码的 demo 数据覆盖）
const NAME_RULES = [
  { re: /\bwomen'?s\b/gi, to: '女款' },
  { re: /\bmen'?s\b/gi, to: '男款' },
  { re: /\bgirl'?s\b/gi, to: '女士' },
  { re: /\bboy'?s\b/gi, to: '男士' },
  { re: /\bsolid\b/gi, to: '纯色' },
  { re: /\bshort sleeve\b/gi, to: '短袖' },
  { re: /\blong sleeve\b/gi, to: '长袖' },
  { re: /\bboat neck\b/gi, to: '船领' },
  { re: /\bv-?neck\b/gi, to: 'V领' },
  { re: /\bcrew neck\b/gi, to: '圆领' },
  { re: /\bhoodie\b/gi, to: '连帽卫衣' },
  { re: /\bjacket\b/gi, to: '夹克' },
  { re: /\bcoat\b/gi, to: '外套' },
  { re: /\btee\b/gi, to: 'T恤' },
  { re: /\bt-?shirt\b/gi, to: 'T恤' },
  { re: /\bshirt\b/gi, to: '衬衫' },
  { re: /\bdress\b/gi, to: '连衣裙' },
  { re: /\bskirt\b/gi, to: '半身裙' },
  { re: /\bjeans\b/gi, to: '牛仔裤' },
  { re: /\bdenim\b/gi, to: '牛仔' },
  { re: /\bleather\b/gi, to: '皮革' },
  { re: /\bsneakers?\b/gi, to: '运动鞋' },
  { re: /\bshoes?\b/gi, to: '鞋' },
  { re: /\brunning\b/gi, to: '跑步' },
  { re: /\boutdoor\b/gi, to: '户外' },
  { re: /\bcasual\b/gi, to: '休闲' },
]

// 常见商品描述短语（demo 数据集里重复率很高的那些）
const DESC_RULES = [
  // 材质
  { re: /\bRAYON\b/gi, to: '人造丝' },
  { re: /\bSPandex\b/gi, to: '氨纶' },
  { re: /\bCOTTON\b/gi, to: '棉' },
  { re: /\bPOLYESTER\b/gi, to: '聚酯纤维' },
  // 句式
  { re: /Made in USA or Imported/gi, to: '美国制造或进口' },
  { re: /Do Not Bleach/gi, to: '请勿漂白' },
  { re: /Lightweight fabric/gi, to: '轻盈面料' },
  { re: /great stretch for comfort/gi, to: '高弹力，更舒适' },
  { re: /Ribbed on sleeves and neckline/gi, to: '袖口与领口罗纹收边' },
  { re: /Hand Wash Only/gi, to: '仅建议手洗' },
  { re: /Machine Wash/gi, to: '可机洗' },
  // 一些常见连接词
  { re: /\bimported\b/gi, to: '进口' },
  { re: /\blightweight\b/gi, to: '轻量' },
  { re: /\bcomfort\b/gi, to: '舒适' },
  { re: /\bstretch\b/gi, to: '弹力' },
]

export function localizeProductName(name) {
  if (!name || typeof name !== 'string') return name || ''
  let out = name
  for (const r of NAME_RULES) out = out.replace(r.re, r.to)
  return normalizeSpaces(out)
}

export function localizeProductDesc(desc) {
  if (!desc || typeof desc !== 'string') return desc || ''
  let out = desc
  for (const r of DESC_RULES) out = out.replace(r.re, r.to)
  return normalizeSpaces(out)
}

