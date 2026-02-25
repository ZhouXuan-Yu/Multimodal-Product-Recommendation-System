#!/usr/bin/env python3
"""
数据库初始化脚本
创建数据库表并插入示例数据
"""

import sys
import os
from pathlib import Path
import random
import json

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.settings import settings
from utils.logger import setup_logging, get_logger
from data.database import db_manager
from data.models import User, Product, UserAction, Recommendation
from core.user_manager import user_manager
from core.product_manager import product_manager

logger = get_logger(__name__)

def create_sample_users():
    """创建示例用户"""
    print("创建示例用户...")

    sample_users = [
        ("admin", "admin", "admin@example.com"),
        ("user1", "123456", "user1@example.com"),
        ("user2", "123456", "user2@example.com"),
        ("alice", "password", "alice@example.com"),
        ("bob", "password", "bob@example.com"),
    ]

    created_users = []
    for username, password, email in sample_users:
        try:
            user = user_manager.register_user(username, password, email)
            created_users.append(user)
            print(f"✓ 创建用户: {username}")
        except Exception as e:
            print(f"✗ 创建用户失败 {username}: {e}")

    return created_users

def create_sample_products():
    """创建示例商品"""
    print("创建示例商品...")

    sample_products = [
        {
            "product_id": "prod_001",
            "title": "iPhone 15 Pro",
            "description": "苹果旗舰手机，A17 Pro芯片，超强性能，专业级摄像头",
            "price": 8999.00,
            "category": "电子产品",
            "rating": 4.8
        },
        {
            "product_id": "prod_002",
            "title": "MacBook Pro 16寸",
            "description": "苹果专业笔记本，M3 Max芯片，超强性能，专业设计师必备",
            "price": 19999.00,
            "category": "电子产品",
            "rating": 4.9
        },
        {
            "product_id": "prod_003",
            "title": "iPad Air",
            "description": "苹果平板电脑，M2芯片，多任务处理，学习娱乐两不误",
            "price": 4799.00,
            "category": "电子产品",
            "rating": 4.7
        },
        {
            "product_id": "prod_004",
            "title": "Nike Air Max",
            "description": "耐克经典跑鞋，舒适透气，时尚百搭，运动必备",
            "price": 899.00,
            "category": "服装鞋包",
            "rating": 4.4
        },
        {
            "product_id": "prod_005",
            "title": "Adidas Ultraboost",
            "description": "阿迪达斯旗舰跑鞋，Boost科技，专业运动鞋",
            "price": 1299.00,
            "category": "服装鞋包",
            "rating": 4.6
        },
        {
            "product_id": "prod_006",
            "title": "Levi's牛仔裤",
            "description": "李维斯经典牛仔裤，优质面料，耐穿耐洗",
            "price": 399.00,
            "category": "服装鞋包",
            "rating": 4.3
        },
        {
            "product_id": "prod_007",
            "title": "Dyson吸尘器",
            "description": "戴森无绳吸尘器，强力吸力，智能控制，家居清洁必备",
            "price": 3999.00,
            "category": "家居用品",
            "rating": 4.7
        },
        {
            "product_id": "prod_008",
            "title": "Philips空气净化器",
            "description": "飞利浦空气净化器，HEPA滤网，除甲醛，健康家居",
            "price": 1999.00,
            "category": "家居用品",
            "rating": 4.5
        },
        {
            "product_id": "prod_009",
            "title": "MUJI收纳箱",
            "description": "无印良品收纳箱，简约设计，实用耐用",
            "price": 89.00,
            "category": "家居用品",
            "rating": 4.3
        },
        {
            "product_id": "prod_010",
            "title": "Python编程书",
            "description": "Python编程从入门到实践，编程学习必备",
            "price": 89.00,
            "category": "图书文具",
            "rating": 4.6
        }
    ]

    created_products = []
    for product_data in sample_products:
        try:
            product = product_manager.add_product(product_data)
            created_products.append(product)
            print(f"✓ 创建商品: {product.title}")
        except Exception as e:
            print(f"✗ 创建商品失败 {product_data['title']}: {e}")

    return created_products

def create_sample_actions(users, products):
    """创建示例用户行为"""
    print("创建示例用户行为...")

    actions = []
    action_types = ['view', 'click', 'favorite', 'purchase']

    for user in users:
        # 每个用户随机生成10-20个行为
        num_actions = random.randint(10, 20)

        for _ in range(num_actions):
            product = random.choice(products)
            action_type = random.choice(action_types)

            # 购买行为较少
            if action_type == 'purchase':
                if random.random() > 0.3:  # 30%概率
                    continue

            try:
                action = UserAction()
                action.user_id = user.user_id
                action.product_id = product.product_id
                action.action_type = action_type
                action.save()
                actions.append(action)
                print(f"✓ 创建行为: {user.username} -> {action_type} -> {product.title}")
            except Exception as e:
                print(f"✗ 创建行为失败: {e}")

    return actions

def create_sample_recommendations(users):
    """创建示例推荐记录"""
    print("创建示例推荐记录...")

    for user in users:
        try:
            # 随机选择一些商品作为推荐结果
            from data.models import Product
            all_products = Product.get_all(limit=20)
            if len(all_products) >= 5:
                recommended_ids = random.sample([p.product_id for p in all_products], 5)

                recommendation = Recommendation()
                recommendation.user_id = user.user_id
                recommendation.recommended_products = recommended_ids
                recommendation.algorithm = "sample_data"
                recommendation.score = round(random.uniform(0.7, 0.95), 3)
                recommendation.save()

                print(f"✓ 创建推荐: {user.username} -> {len(recommended_ids)}个商品")
        except Exception as e:
            print(f"✗ 创建推荐失败 {user.username}: {e}")

def main():
    """主函数"""
    print("多模态商品推荐系统 - 数据库初始化")
    print("=" * 50)

    # 初始化日志
    setup_logging()

    try:
        # 检查数据库连接
        print("检查数据库连接...")
        if not db_manager.health_check():
            print("✗ 数据库连接失败，请检查配置")
            return 1
        print("✓ 数据库连接成功")

        # 创建表结构
        print("创建数据库表...")
        db_manager.create_tables()
        print("✓ 数据库表创建成功")

        # 创建示例数据
        users = create_sample_users()
        products = create_sample_products()
        actions = create_sample_actions(users, products)
        create_sample_recommendations(users)

        # 显示统计信息
        print("\n数据初始化完成！")
        stats = db_manager.get_stats()
        print(f"用户数量: {stats.get('user_count', 0)}")
        print(f"商品数量: {stats.get('product_count', 0)}")
        print(f"行为记录: {stats.get('action_count', 0)}")
        print(f"推荐记录: {stats.get('recommendation_count', 0)}")

        print("\n✓ 数据库初始化成功！")
        return 0

    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        print(f"✗ 数据库初始化失败: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())

