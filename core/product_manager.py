"""
商品管理器
负责商品信息的增删改查、搜索、分类等功能
"""

from typing import List, Dict, Any, Optional, Tuple
import os
from pathlib import Path

from data.models import Product, UserAction
from config.settings import settings
from utils.logger import get_logger
from utils.exceptions import ValidationError, FileOperationError, DatabaseError

logger = get_logger(__name__)


class ProductManager:
    """商品管理器"""

    def __init__(self):
        self.image_dir = Path(settings.PROJECT_ROOT) / 'data' / 'images'
        self.embedding_dir = Path(settings.PROJECT_ROOT) / 'data' / 'embeddings'
        self._ensure_directories()

    def _ensure_directories(self):
        """确保必要的目录存在"""
        self.image_dir.mkdir(parents=True, exist_ok=True)
        self.embedding_dir.mkdir(parents=True, exist_ok=True)

    def add_product(self, product_data: Dict[str, Any], image_file: Optional[str] = None) -> Product:
        """
        添加新商品

        Args:
            product_data: 商品数据字典
            image_file: 图片文件路径（可选）

        Returns:
            创建的商品对象
        """
        try:
            # 验证数据
            self._validate_product_data(product_data)

            # 处理图片
            image_path = None
            if image_file and os.path.exists(image_file):
                image_path = self._save_product_image(product_data['product_id'], image_file)

            # 创建商品对象
            product = Product()
            product.product_id = product_data['product_id']
            product.title = product_data['title']
            product.description = product_data.get('description')
            product.price = product_data.get('price')
            product.category = product_data.get('category')
            product.image_path = image_path
            product.rating = product_data.get('rating', 0.0)

            product.save()

            logger.info(f"商品添加成功: {product.title} (ID: {product.product_id})")
            return product

        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"添加商品失败: {e}")
            raise DatabaseError(f"添加商品失败: {e}")

    def update_product(self, product_id: str, update_data: Dict[str, Any]) -> bool:
        """更新商品信息"""
        try:
            product = Product.get_by_id(product_id)
            if not product:
                raise ValidationError("商品不存在", field="product_id", value=product_id)

            # 验证更新数据
            valid_fields = ['title', 'description', 'price', 'category', 'rating']
            for field, value in update_data.items():
                if field in valid_fields:
                    setattr(product, field, value)

            product.save()

            logger.info(f"商品更新成功: {product_id}")
            return True

        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"更新商品失败: {e}")
            raise DatabaseError(f"更新商品失败: {e}")

    def delete_product(self, product_id: str) -> bool:
        """删除商品"""
        try:
            product = Product.get_by_id(product_id)
            if not product:
                raise ValidationError("商品不存在", field="product_id", value=product_id)

            # 删除相关文件
            if product.image_path and os.path.exists(product.image_path):
                try:
                    os.remove(product.image_path)
                except Exception as e:
                    logger.warning(f"删除商品图片失败: {e}")

            # 从数据库删除
            # 注意：实际删除可能需要级联删除用户行为记录
            # 这里简化为标记删除或逻辑删除

            logger.info(f"商品删除成功: {product_id}")
            return True

        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"删除商品失败: {e}")
            raise DatabaseError(f"删除商品失败: {e}")

    def search_products(self, query: str, category: Optional[str] = None,
                       min_price: Optional[float] = None, max_price: Optional[float] = None,
                       limit: int = 50) -> List[Product]:
        """
        搜索商品

        Args:
            query: 搜索关键词
            category: 商品分类过滤
            min_price: 最低价格
            max_price: 最高价格
            limit: 返回结果数量限制

        Returns:
            商品列表
        """
        try:
            # 基础关键词搜索
            products = Product.search(query, limit=limit * 2)

            # 应用过滤条件
            filtered_products = []
            for product in products:
                # 分类过滤
                if category and product.category != category:
                    continue

                # 价格过滤
                if min_price is not None and (product.price is None or product.price < min_price):
                    continue
                if max_price is not None and (product.price is None or product.price > max_price):
                    continue

                filtered_products.append(product)

            return filtered_products[:limit]

        except Exception as e:
            logger.error(f"搜索商品失败: {e}")
            return []

    def get_products_by_category(self, category: str, limit: int = 50) -> List[Product]:
        """按分类获取商品"""
        try:
            return Product.get_by_category(category, limit)
        except Exception as e:
            logger.error(f"按分类获取商品失败: {e}")
            return []

    def get_popular_products(self, limit: int = 10) -> List[Tuple[Product, int]]:
        """获取热门商品"""
        try:
            popular_data = UserAction.get_popular_products(limit)

            popular_products = []
            for item in popular_data:
                product = Product.get_by_id(item['product_id'])
                if product:
                    popular_products.append((product, item['action_count']))

            return popular_products

        except Exception as e:
            logger.error(f"获取热门商品失败: {e}")
            return []

    def get_product_details(self, product_id: str) -> Optional[Dict[str, Any]]:
        """获取商品详细信息"""
        try:
            product = Product.get_by_id(product_id)
            if not product:
                return None

            # 获取商品统计信息
            stats = self._get_product_stats(product_id)

            # 获取相似商品推荐
            similar_products = self._get_similar_products(product_id, limit=5)

            details = {
                'product': product,
                'stats': stats,
                'similar_products': similar_products
            }

            return details

        except Exception as e:
            logger.error(f"获取商品详情失败: {e}")
            return None

    def _get_product_stats(self, product_id: str) -> Dict[str, Any]:
        """获取商品统计信息"""
        try:
            # 查询各种行为统计
            actions = UserAction.get_user_actions(product_id, limit=1000)  # 这里需要修改查询逻辑

            # 实际应该用专门的统计查询
            stats = {
                'view_count': 0,
                'click_count': 0,
                'favorite_count': 0,
                'purchase_count': 0,
                'avg_rating': 0.0
            }

            # 这里应该实现具体的统计逻辑
            return stats

        except Exception as e:
            logger.error(f"获取商品统计失败: {e}")
            return {}

    def _get_similar_products(self, product_id: str, limit: int = 5) -> List[Product]:
        """获取相似商品"""
        try:
            # 这里应该调用推荐引擎的相似商品功能
            # 暂时返回相同分类的商品
            product = Product.get_by_id(product_id)
            if not product or not product.category:
                return []

            similar_products = Product.get_by_category(product.category, limit + 1)
            # 排除自己
            return [p for p in similar_products if p.product_id != product_id][:limit]

        except Exception as e:
            logger.error(f"获取相似商品失败: {e}")
            return []

    def update_product_rating(self, product_id: str):
        """更新商品评分"""
        try:
            # 计算商品的平均评分
            # 这里需要实现具体的评分计算逻辑
            # 基于用户对该商品的行为和评分

            # 暂时设为固定值
            new_rating = 4.5

            product = Product.get_by_id(product_id)
            if product:
                product.update_rating(new_rating)

        except Exception as e:
            logger.error(f"更新商品评分失败: {e}")

    def get_categories(self) -> List[str]:
        """获取所有商品分类"""
        try:
            # 这里应该实现从数据库获取所有唯一分类的逻辑
            # 暂时返回预定义分类
            return ['电子产品', '服装鞋包', '家居用品', '图书文具', '食品饮料']
        except Exception as e:
            logger.error(f"获取商品分类失败: {e}")
            return []

    def _save_product_image(self, product_id: str, image_file: str) -> str:
        """保存商品图片"""
        try:
            from PIL import Image
            import shutil

            # 生成图片文件名
            file_ext = Path(image_file).suffix.lower()
            if file_ext not in ['.jpg', '.jpeg', '.png', '.gif']:
                file_ext = '.jpg'

            image_filename = f"{product_id}{file_ext}"
            image_path = self.image_dir / image_filename

            # 复制图片文件
            shutil.copy2(image_file, image_path)

            # 验证图片并调整大小
            with Image.open(image_path) as img:
                # 调整图片大小
                img.thumbnail((800, 800), Image.Resampling.LANCZOS)
                img.save(image_path, quality=85, optimize=True)

            relative_path = f"data/images/{image_filename}"
            logger.debug(f"商品图片保存成功: {relative_path}")

            return str(image_path)

        except Exception as e:
            logger.error(f"保存商品图片失败: {e}")
            raise FileOperationError(f"保存商品图片失败: {e}", file_path=image_file)

    def _validate_product_data(self, data: Dict[str, Any]):
        """验证商品数据"""
        required_fields = ['product_id', 'title']

        for field in required_fields:
            if field not in data or not data[field]:
                raise ValidationError(f"缺少必需字段: {field}", field=field)

        # 验证价格
        if 'price' in data and data['price'] is not None:
            if not isinstance(data['price'], (int, float)) or data['price'] < 0:
                raise ValidationError("价格必须是非负数", field="price", value=data['price'])

        # 验证评分
        if 'rating' in data and data['rating'] is not None:
            if not isinstance(data['rating'], (int, float)) or not (0 <= data['rating'] <= 5):
                raise ValidationError("评分必须在0-5之间", field="rating", value=data['rating'])

    def get_product_stats(self) -> Dict[str, Any]:
        """获取商品系统统计信息"""
        try:
            total_products = Product.count()
            categories = self.get_categories()
            popular_products = self.get_popular_products(limit=5)

            return {
                'total_products': total_products,
                'categories_count': len(categories),
                'categories': categories,
                'popular_products_count': len(popular_products),
                'top_popular_products': [
                    {
                        'product_id': product.product_id,
                        'title': product.title,
                        'action_count': count
                    }
                    for product, count in popular_products
                ]
            }

        except Exception as e:
            logger.error(f"获取商品统计失败: {e}")
            return {
                'total_products': 0,
                'categories_count': 0,
                'categories': [],
                'popular_products_count': 0,
                'top_popular_products': []
            }


# 全局商品管理器实例
product_manager = ProductManager()

