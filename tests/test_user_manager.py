"""
用户管理器测试
"""

import unittest
from unittest.mock import patch, MagicMock

from tests.base_test import BaseTestCase
from core.user_manager import UserManager
from utils.exceptions import AuthenticationError, ValidationError


class TestUserManager(BaseTestCase):
    """用户管理器测试类"""

    def setUp(self):
        super().setUp()
        self.user_manager = UserManager()

    def test_register_user_success(self):
        """测试用户注册成功"""
        with patch('core.user_manager.User') as mock_user_class:
            # 模拟用户创建
            mock_user = MagicMock()
            mock_user.user_id = "test_user_id"
            mock_user.username = "testuser"
            mock_user_class.create_user.return_value = mock_user
            mock_user_class.get_by_username.return_value = None

            # 执行注册
            result = self.user_manager.register_user("testuser", "password123", "test@example.com")

            # 验证结果
            self.assertEqual(result, mock_user)
            mock_user_class.create_user.assert_called_once()
            mock_user.save.assert_called_once()

    def test_register_user_duplicate_username(self):
        """测试注册重复用户名"""
        with patch('core.user_manager.User') as mock_user_class:
            # 模拟已存在的用户
            mock_existing_user = MagicMock()
            mock_user_class.get_by_username.return_value = mock_existing_user

            # 验证异常
            with self.assertRaises(ValidationError) as context:
                self.user_manager.register_user("existinguser", "password123")

            self.assertIn("用户名已存在", str(context.exception))

    def test_register_user_invalid_username(self):
        """测试注册无效用户名"""
        # 用户名太短
        with self.assertRaises(ValidationError):
            self.user_manager.register_user("ab", "password123")

        # 用户名包含无效字符
        with self.assertRaises(ValidationError):
            self.user_manager.register_user("user@name", "password123")

    def test_authenticate_user_success(self):
        """测试用户登录成功"""
        with patch('core.user_manager.User') as mock_user_class:
            # 模拟用户
            mock_user = MagicMock()
            mock_user.username = "testuser"
            mock_user.verify_password.return_value = True
            mock_user_class.get_by_username.return_value = mock_user

            # 执行登录
            result = self.user_manager.authenticate_user("testuser", "password123")

            # 验证结果
            self.assertEqual(result, mock_user)
            self.assertEqual(self.user_manager.current_user, mock_user)
            mock_user.verify_password.assert_called_once_with("password123")

    def test_authenticate_user_wrong_password(self):
        """测试登录密码错误"""
        with patch('core.user_manager.User') as mock_user_class:
            # 模拟用户
            mock_user = MagicMock()
            mock_user.verify_password.return_value = False
            mock_user_class.get_by_username.return_value = mock_user

            # 验证异常
            with self.assertRaises(AuthenticationError) as context:
                self.user_manager.authenticate_user("testuser", "wrongpassword")

            self.assertIn("密码错误", str(context.exception))

    def test_authenticate_user_not_found(self):
        """测试登录用户不存在"""
        with patch('core.user_manager.User') as mock_user_class:
            mock_user_class.get_by_username.return_value = None

            # 验证异常
            with self.assertRaises(AuthenticationError) as context:
                self.user_manager.authenticate_user("nonexistent", "password123")

            self.assertIn("用户名不存在", str(context.exception))

    def test_logout_user(self):
        """测试用户登出"""
        # 设置当前用户
        self.user_manager.current_user = MagicMock()
        self.user_manager.current_user.username = "testuser"

        # 执行登出
        self.user_manager.logout_user()

        # 验证结果
        self.assertIsNone(self.user_manager.current_user)

    def test_update_user_preferences(self):
        """测试更新用户偏好"""
        with patch('core.user_manager.User') as mock_user_class:
            # 模拟用户
            mock_user = MagicMock()
            mock_user_class.get_by_id.return_value = mock_user

            # 执行更新
            preferences = {"theme": "dark", "language": "zh_CN"}
            self.user_manager.update_user_preferences("user_id", preferences)

            # 验证结果
            mock_user.update_preferences.assert_called_once_with(preferences)

    def test_update_user_preferences_user_not_found(self):
        """测试更新不存在用户的偏好"""
        with patch('core.user_manager.User') as mock_user_class:
            mock_user_class.get_by_id.return_value = None

            with self.assertRaises(ValidationError) as context:
                self.user_manager.update_user_preferences("nonexistent", {"theme": "dark"})

            self.assertIn("用户不存在", str(context.exception))


if __name__ == '__main__':
    unittest.main()

