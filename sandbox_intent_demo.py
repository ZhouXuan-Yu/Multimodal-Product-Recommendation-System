"""简单终端测试脚本：验证 SmartRecommendationEngine 是否能跑通 DeepSeek 查询意图解析。"""

from core.recommendation_engine import SmartRecommendationEngine


def main() -> None:
    engine = SmartRecommendationEngine()

    # 你可以根据需要修改这个 query 文本
    query = "预算两千左右，想要一款适合大学生的轻薄游戏本，最好有独立显卡"

    intent = engine.analyze_intent(
        user_id="test_user_001",
        query=query,
        user_profile={},
        history=[],
        timeout=30,
    )

    print("=== DeepSeek 查询意图解析结果 ===")
    print(intent)


if __name__ == "__main__":
    main()

