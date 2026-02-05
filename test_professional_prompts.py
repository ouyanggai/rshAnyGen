#!/usr/bin/env python3
"""
测试专业提示词效果
"""
import asyncio
import json
from apps.gateway.services.context_builder import get_context_builder
from apps.orchestrator.graph.nodes.llm_generator import _build_prompt
from apps.orchestrator.services.llm_client import LLMClient
from apps.shared.config_loader import ConfigLoader
from apps.shared.logger import LogManager

config = ConfigLoader()
logger_manager = LogManager("test")
logger = logger_manager.get_logger()

async def test_prompt_scenario(scenario_name, state, expected_keywords=None):
    """测试单个场景的提示词"""
    print(f"\n{'='*60}")
    print(f"  测试场景: {scenario_name}")
    print(f"{'='*60}")

    # 1. 生成提示词
    prompt = _build_prompt(state)
    print(f"\n📝 提示词长度: {len(prompt)} 字符")
    print(f"\n🔍 提示词结构检查:")
    print(f"   - 包含企业身份: {'润世华集团' in prompt}")
    print(f"   - 包含用户信息: {'系统上下文' in prompt}")
    print(f"   - 包含对话历史: {'对话上下文' in prompt}")
    print(f"   - 包含回答规范: {'回答规范' in prompt}")

    # 2. 显示提示词摘要
    print(f"\n📄 提示词摘要:")
    print("-" * 60)
    lines = prompt.split('\n')
    for line in lines[:30]:  # 显示前30行
        print(line)
    if len(lines) > 30:
        print(f"... (还有 {len(lines) - 30} 行)")
    print("-" * 60)

    # 3. 调用 LLM
    print(f"\n🤖 调用 LLM...")
    llm_config = state.get("llm_config") or {}
    client = LLMClient(
        api_key=llm_config.get("api_key"),
        base_url=llm_config.get("base_url")
    )
    llm = client.get_chat_model(temperature=0.7)

    response = await llm.ainvoke(prompt, config={"tags": ["final_answer"]})
    answer = response.content

    print(f"\n✅ LLM 回答:")
    print("-" * 60)
    print(answer)
    print("-" * 60)

    # 4. 验证回答质量
    print(f"\n🎯 回答质量检查:")

    # 检查企业身份
    has_enterprise = "润世华" in answer or "集团" in answer or "欧阳改" in answer
    print(f"   - 体现企业身份: {has_enterprise}")

    # 检查专业性
    has_professional = any(word in answer for word in ["根据", "建议", "提供", "基于"])
    print(f"   - 体现专业性: {has_professional}")

    # 检查礼貌用语
    has_polite = any(word in answer for word in ["您", "您好", "请问", "谢谢"])
    print(f"   - 使用礼貌用语: {has_polite}")

    # 检查结构化
    has_structure = "\n" in answer and len(answer) > 50
    print(f"   - 结构化表达: {has_structure}")

    # 检查预期关键词
    if expected_keywords:
        has_expected = any(keyword in answer for keyword in expected_keywords)
        print(f"   - 包含预期关键词: {has_expected} {expected_keywords}")

    # 综合评分
    quality_score = sum([
        has_enterprise,
        has_professional,
        has_polite,
        has_structure
    ])
    print(f"\n⭐ 专业性评分: {quality_score}/4")

    return {
        "prompt_length": len(prompt),
        "has_enterprise": has_enterprise,
        "has_professional": has_professional,
        "has_polite": has_polite,
        "has_structure": has_structure,
        "quality_score": quality_score,
        "answer": answer
    }

async def test_all_scenarios():
    """测试所有场景"""
    print("🧪 测试专业提示词效果")
    print("=" * 60)

    user_id = "e77a36c0-429f-4bb6-8a07-382a52bf44c3"
    session_id = "test-professional-prompts"

    # 场景1: RAG知识库问答
    print("\n\n" + "🔍 场景1: RAG知识库问答")
    print("=" * 60)

    context_builder = get_context_builder("qwen-max")
    context_messages = await context_builder.build_context(
        session_id=session_id,
        user_id=user_id,
        current_message="公司的年假政策是什么？"
    )

    state_rag = {
        "session_id": session_id,
        "user_message": "公司的年假政策是什么？",
        "messages": context_messages,
        "intent": "chat",
        "retrieved_docs": [
            {
                "score": 0.95,
                "content": "润世华集团年假政策：工作满1年不满10年：年休假5天；工作满10年不满20年：年休假10天；工作满20年：年休假15天。",
                "metadata": {"source": "HR政策文件"}
            }
        ],
        "tool_results": None
    }

    result1 = await test_prompt_scenario("RAG知识库问答", state_rag)

    # 场景2: 搜索场景
    print("\n\n🔍 场景2: 联网搜索问答")
    print("=" * 60)

    state_search = {
        "session_id": session_id,
        "user_message": "2024年最新的企业所得税优惠政策有哪些？",
        "messages": context_messages,
        "intent": "search",
        "retrieved_docs": [],
        "tool_results": "根据最新政策，小微企业减按25%征收企业所得税，实际税率5%。研发费用加计扣除比例提高至100%..."
    }

    result2 = await test_prompt_scenario("联网搜索问答", state_search, ["企业所得税", "小微企业"])

    # 场景3: 通用问答
    print("\n\n🔍 场景3: 通用日常问答")
    print("=" * 60)

    state_general = {
        "session_id": session_id,
        "user_message": "你好，我想了解一下如何提高工作效率",
        "messages": context_messages,
        "intent": "chat",
        "retrieved_docs": [],
        "tool_results": None
    }

    result3 = await test_prompt_scenario("通用日常问答", state_general, ["欧阳改", "建议"])

    # 总结
    print("\n\n" + "=" * 60)
    print("  测试总结")
    print("=" * 60)

    print(f"\n📊 各场景评分:")
    print(f"   1. RAG知识库问答: {result1['quality_score']}/4")
    print(f"   2. 联网搜索问答: {result2['quality_score']}/4")
    print(f"   3. 通用日常问答: {result3['quality_score']}/4")

    avg_score = (result1['quality_score'] + result2['quality_score'] + result3['quality_score']) / 3
    print(f"\n⭐ 平均专业性评分: {avg_score:.1f}/4")

    if avg_score >= 3.0:
        print("\n✅ 提示词质量优秀！")
    elif avg_score >= 2.0:
        print("\n✅ 提示词质量良好")
    else:
        print("\n⚠️ 提示词需要优化")

    return avg_score

if __name__ == "__main__":
    result = asyncio.run(test_all_scenarios())
    exit(0 if result >= 2.0 else 1)
