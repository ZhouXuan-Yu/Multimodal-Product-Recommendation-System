#!/usr/bin/env python3
"""
数据集下载和预处理脚本（training 包）
下载电商商品多模态数据集并进行预处理
"""

import os
import sys
import requests
import zipfile
import pandas as pd
import numpy as np
from pathlib import Path
import argparse
from tqdm import tqdm
import json
from PIL import Image
import shutil

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.logger import get_logger

logger = get_logger(__name__)

class DatasetDownloader:
    """数据集下载器"""

    def __init__(self, data_dir="data"):
        self.data_dir = Path(data_dir)
        self.raw_data_dir = self.data_dir / "raw"
        self.processed_data_dir = self.data_dir / "processed"
        self.images_dir = self.data_dir / "images"
        self.embeddings_dir = self.data_dir / "embeddings"

        # 创建目录
        for dir_path in [self.raw_data_dir, self.processed_data_dir,
                        self.images_dir, self.embeddings_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)

        # 数据集配置
        self.datasets = {
            "amazon_fashion": {
                "url": "https://datarepo.eng.ucsd.edu/mcauley_group/data/amazon_v2/categoryFilesSmall/AMAZON_FASHION.json.gz",
                "filename": "AMAZON_FASHION.json.gz",
                "description": "Amazon时尚商品数据集"
            },
            "amazon_electronics": {
                "url": "https://datarepo.eng.ucsd.edu/mcauley_group/data/amazon_v2/categoryFilesSmall/Electronics.json.gz",
                "filename": "Electronics.json.gz",
                "description": "Amazon电子产品数据集"
            },
            "sample_images": {
                "url": "https://github.com/alexeygrigorev/clothing-dataset-small/archive/refs/heads/master.zip",
                "filename": "clothing-dataset-small.zip",
                "description": "服装图像样本数据集"
            }
        }

    def download_file(self, url, filename, description=""):
        """下载文件"""
        filepath = self.raw_data_dir / filename

        if filepath.exists():
            logger.info(f"{description} 已存在，跳过下载")
            return filepath

        logger.info(f"正在下载 {description}...")
        try:
            response = requests.get(url, stream=True, timeout=300)
            response.raise_for_status()

            total_size = int(response.headers.get('content-length', 0))

            with open(filepath, 'wb') as f, tqdm(
                desc=f"下载 {filename}",
                total=total_size,
                unit='B',
                unit_scale=True,
                unit_divisor=1024,
            ) as pbar:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        pbar.update(len(chunk))

            logger.info(f"{description} 下载完成")
            return filepath

        except Exception as e:
            logger.error(f"下载失败: {e}")
            return None

    def extract_zip(self, zip_path, extract_to):
        """解压ZIP文件"""
        logger.info(f"正在解压 {zip_path}...")
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_to)
            logger.info("解压完成")
            return True
        except Exception as e:
            logger.error(f"解压失败: {e}")
            return False

    def download_amazon_data(self):
        """下载Amazon数据集"""
        logger.info("开始下载Amazon数据集...")

        for name, config in self.datasets.items():
            if "amazon" in name:
                url_variants = [config["url"]]
                # add a few heuristic variants to try if original path returns 404
                url_variants.append(config["url"].replace("categoryFilesSmall", "categoryFiles"))
                url_variants.append(config["url"].replace("categoryFilesSmall", "categoryFilesSmall").replace("AMAZON_FASHION", "amazon_fashion"))
                url_variants.append(config["url"].replace("categoryFilesSmall", "categoryFilesSmall").replace("Electronics", "electronics"))

                filepath = None
                for try_url in url_variants:
                    logger.info(f"尝试下载 {config['description']} 从 {try_url} ...")
                    filepath = self.download_file(try_url, config["filename"], config["description"])
                    if filepath:
                        logger.info(f"{name} 下载成功: {filepath}")
                        break

                if not filepath:
                    logger.warning(f"{name} 无可用 URL，已跳过该数据集（请手动提供或更新 URL）")

        return True

    def download_image_data(self):
        """下载图像数据集"""
        logger.info("开始下载图像数据集...")

        config = self.datasets["sample_images"]
        zip_path = self.download_file(
            config["url"],
            config["filename"],
            config["description"]
        )

        if zip_path and self.extract_zip(zip_path, self.raw_data_dir):
            # 移动图像到images目录
            extracted_dir = self.raw_data_dir / "clothing-dataset-small-master"
            if extracted_dir.exists():
                for img_file in extracted_dir.glob("**/*.jpg"):
                    shutil.copy2(img_file, self.images_dir / img_file.name)
                logger.info("图像文件已复制到images目录")

        return True

    def create_sample_dataset(self):
        """创建示例数据集"""
        logger.info("创建示例商品数据集...")

        # 示例商品数据
        sample_products = [
            {
                "product_id": "P001",
                "title": "Nike Air Max 270",
                "description": "舒适的运动鞋，适合日常穿着和运动",
                "category": "鞋类",
                "price": 899.00,
                "rating": 4.5,
                "image_path": "nike_air_max.jpg",
                "tags": ["运动鞋", "Nike", "舒适", "时尚"]
            },
            {
                "product_id": "P002",
                "title": "Apple MacBook Pro 14寸",
                "description": "专业级笔记本电脑，M2芯片，性能卓越",
                "category": "电子产品",
                "price": 14999.00,
                "rating": 4.8,
                "image_path": "macbook_pro.jpg",
                "tags": ["笔记本", "Apple", "M2", "专业"]
            },
            {
                "product_id": "P003",
                "title": "Sony WH-1000XM4 头戴式耳机",
                "description": "主动降噪无线耳机，音质出众",
                "category": "电子产品",
                "price": 2499.00,
                "rating": 4.6,
                "image_path": "sony_wh1000xm4.jpg",
                "tags": ["耳机", "Sony", "降噪", "无线"]
            },
            {
                "product_id": "P004",
                "title": "Levi's 501牛仔裤",
                "description": "经典直筒牛仔裤，舒适耐穿",
                "category": "服装",
                "price": 599.00,
                "rating": 4.3,
                "image_path": "levis_501.jpg",
                "tags": ["牛仔裤", "Levi's", "经典", "舒适"]
            },
            {
                "product_id": "P005",
                "title": "Dyson V8吸尘器",
                "description": "无绳吸尘器，强劲吸力，方便易用",
                "category": "家居",
                "price": 3499.00,
                "rating": 4.7,
                "image_path": "dyson_v8.jpg",
                "tags": ["吸尘器", "Dyson", "无绳", "强劲"]
            }
        ]

        # 保存为JSON
        products_file = self.processed_data_dir / "products.json"
        with open(products_file, 'w', encoding='utf-8') as f:
            json.dump(sample_products, f, ensure_ascii=False, indent=2)

        # 创建用户数据
        sample_users = [
            {
                "user_id": "U001",
                "username": "user1",
                "preferences": ["电子产品", "时尚"],
                "age": 25,
                "gender": "female"
            },
            {
                "user_id": "U002",
                "username": "user2",
                "preferences": ["运动", "户外"],
                "age": 30,
                "gender": "male"
            }
        ]

        users_file = self.processed_data_dir / "users.json"
        with open(users_file, 'w', encoding='utf-8') as f:
            json.dump(sample_users, f, ensure_ascii=False, indent=2)

        # 创建交互数据
        sample_interactions = [
            {"user_id": "U001", "product_id": "P001", "action": "view", "rating": 5},
            {"user_id": "U001", "product_id": "P002", "action": "purchase", "rating": 4},
            {"user_id": "U002", "product_id": "P001", "action": "favorite", "rating": 5},
            {"user_id": "U002", "product_id": "P004", "action": "view", "rating": 3},
        ]

        interactions_file = self.processed_data_dir / "interactions.json"
        with open(interactions_file, 'w', encoding='utf-8') as f:
            json.dump(sample_interactions, f, ensure_ascii=False, indent=2)

        logger.info("示例数据集创建完成")
        logger.info(f"商品数据: {len(sample_products)} 条")
        logger.info(f"用户数据: {len(sample_users)} 条")
        logger.info(f"交互数据: {len(sample_interactions)} 条")

        return True

    def download_all(self):
        """下载所有数据集"""
        logger.info("开始下载所有数据集...")

        try:
            # 下载Amazon数据集
            self.download_amazon_data()

            # 下载图像数据
            self.download_image_data()

            # 创建示例数据集
            self.create_sample_dataset()

            logger.info("所有数据集下载完成！")
            return True

        except Exception as e:
            logger.error(f"数据集下载失败: {e}")
            return False

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="下载和预处理数据集")
    parser.add_argument("--data-dir", default="data", help="数据目录")
    parser.add_argument("--dataset", choices=["amazon", "images", "sample", "all"],
                       default="all", help="要下载的数据集类型")

    args = parser.parse_args()

    downloader = DatasetDownloader(args.data_dir)

    if args.dataset == "amazon":
        downloader.download_amazon_data()
    elif args.dataset == "images":
        downloader.download_image_data()
    elif args.dataset == "sample":
        downloader.create_sample_dataset()
    else:
        downloader.download_all()

if __name__ == "__main__":
    main()


