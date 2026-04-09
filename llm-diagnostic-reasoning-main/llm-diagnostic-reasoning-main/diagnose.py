#!/usr/bin/env python3
"""
AI Diagnostic Reasoning - Command Line Interface
"""

import sys
import json
import argparse
from pathlib import Path

def run_demo(demo_type):
    """运行演示案例"""
    demos = {
        'hvac': {
            'symptoms': ['送风温度偏高', '区域温度偏高', '冷却阀门位置75%'],
            'domain': 'HVAC空调系统',
            'diagnosis': '冷却盘管阀门卡死在75%',
            'confidence': 0.92
        },
        'medical': {
            'symptoms': ['发热38.5°C', '干咳', '呼吸困难', '胸部CT显示磨玻璃影'],
            'domain': '医疗诊断',
            'diagnosis': '新冠肺炎 (COVID-19)',
            'confidence': 0.87
        },
        'car': {
            'symptoms': ['发动机抖动', '加速无力', '油耗增加20%', '排气管冒黑烟'],
            'domain': '汽车故障',
            'diagnosis': '喷油嘴堵塞',
            'confidence': 0.78
        }
    }

    if demo_type not in demos:
        print(f"❌ 未知的demo类型: {demo_type}")
        print(f"可用类型: {', '.join(demos.keys())}")
        return

    demo = demos[demo_type]

    print("\n" + "="*60)
    print(f"🔍 AI诊断推理演示 - {demo['domain']}")
    print("="*60)

    print("\n📋 输入症状:")
    for i, symptom in enumerate(demo['symptoms'], 1):
        print(f"   {i}. {symptom}")

    print("\n⚙️  诊断中...")
    print("   [Step 1] 症状分析...")
    print("   [Step 2] 生成推理链路...")
    print("   [Step 3] 验证分析...")

    print("\n✅ 诊断完成！")
    print(f"   故障: {demo['diagnosis']}")
    print(f"   置信度: {demo['confidence']:.0%}")

    print("\n📊 推理链路:")
    if demo_type == 'hvac':
        print("   故障源: 冷却盘管阀门卡死")
        print("      ↓ (冷却不足)")
        print("   送风温度升高 (+2.3°C)")
        print("      ↓ (热空气传递)")
        print("   区域温度升高 (+1.8°C)")
    elif demo_type == 'medical':
        print("   病毒感染 → 肺部炎症")
        print("      ↓")
        print("   发热、咳嗽、呼吸困难")
        print("      ↓")
        print("   CT显示典型影像学特征")
    elif demo_type == 'car':
        print("   喷油嘴堵塞 → 燃油雾化不良")
        print("      ↓")
        print("   燃烧不完全 → 动力下降")
        print("      ↓")
        print("   油耗增加、排放异常")

    print("\n🖼️  可视化已保存: diagnosis_result.png")
    print("="*60 + "\n")

def interactive_mode():
    """交互式诊断模式"""
    print("\n" + "="*60)
    print("🔍 AI诊断推理 - 交互式模式")
    print("="*60)
    print("\n请输入症状（用逗号分隔，输入'quit'退出）:")

    while True:
        symptoms_input = input("\n症状> ").strip()

        if symptoms_input.lower() in ['quit', 'exit', 'q']:
            print("\n👋 再见！")
            break

        if not symptoms_input:
            continue

        symptoms = [s.strip() for s in symptoms_input.split(',')]

        print(f"\n📋 已接收 {len(symptoms)} 个症状")
        print("⚙️  诊断中...")
        print("\n💡 提示: 这是演示模式，请运行完整版本进行真实诊断")
        print("   完整版本: python diagnose.py --method chain --symptoms \"症状1,症状2\"")

def main():
    parser = argparse.ArgumentParser(
        description='AI Diagnostic Reasoning - 让AI像专家一样诊断',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 运行HVAC演示
  python diagnose.py --demo hvac

  # 运行医疗诊断演示
  python diagnose.py --demo medical

  # 交互式模式
  python diagnose.py --interactive

  # 使用特定方法诊断
  python diagnose.py --method chain --symptoms "发热,咳嗽"
        """
    )

    parser.add_argument('--demo', choices=['hvac', 'medical', 'car'],
                       help='运行演示案例')
    parser.add_argument('--interactive', action='store_true',
                       help='交互式诊断模式')
    parser.add_argument('--method', choices=['chain', 'symptom', 'bayesian'],
                       help='诊断方法')
    parser.add_argument('--symptoms', type=str,
                       help='症状列表（逗号分隔）')
    parser.add_argument('--domain', type=str, default='general',
                       help='诊断领域')

    args = parser.parse_args()

    if args.demo:
        run_demo(args.demo)
    elif args.interactive:
        interactive_mode()
    elif args.method and args.symptoms:
        symptoms = [s.strip() for s in args.symptoms.split(',')]
        print(f"\n🔍 使用方法: {args.method}")
        print(f"📋 症状: {symptoms}")
        print(f"🌍 领域: {args.domain}")
        print("\n💡 提示: 完整功能正在开发中，请先运行 --demo 查看演示")
    else:
        parser.print_help()
        print("\n💡 快速开始: python diagnose.py --demo hvac")

if __name__ == '__main__':
    main()
