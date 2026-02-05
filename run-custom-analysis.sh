#!/bin/bash

# 自定义分析启动脚本
echo "╔════════════════════════════════════════╗"
echo "║  TrendRadar 自定义分析模块             ║"
echo "╚════════════════════════════════════════╝"
echo ""

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "❌ [错误] 虚拟环境未找到"
    echo "请先创建虚拟环境：python3 -m venv venv"
    echo ""
    exit 1
fi

# 激活虚拟环境
echo "[步骤] 激活虚拟环境"
source venv/bin/activate

# 运行自定义分析
echo "[步骤] 执行自定义分析"
echo ""
python extensions/custom_analysis.py

# 检查执行结果
if [ $? -eq 0 ]; then
    echo ""
    echo "✅ [成功] 自定义分析执行完成"
else
    echo ""
    echo "❌ [错误] 自定义分析执行失败"
    exit 1
fi

echo ""
echo "📝 分析结果已保存到：output/analysis/custom_analysis.json"
echo ""
echo "💡 提示："
echo "- 该分析每天只执行一次，避免过度消耗token"
echo "- 分析结果会推送到独立展示区"
echo "- 你可以在配置文件中调整分析参数"
echo ""
