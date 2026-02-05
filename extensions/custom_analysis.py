#!/usr/bin/env python3
# coding=utf-8
"""
自定义AI分析模块

功能：
1. 分析output目录中的全部文本数据
2. 生成与国际局势、中国大事、社会新闻相关的公众号写作方向
3. 一天只运行一次，避免过度消耗token
4. 将分析结果推送到独立展示区
"""

import os
import sys
import json
import sqlite3
import datetime
import traceback
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from trendradar.context import AppContext
from trendradar.notification import NotificationDispatcher
from trendradar.ai.analyzer import AIAnalyzer
from trendradar.core import load_config

class CustomAnalyzer:
    """自定义分析器"""
    
    def __init__(self):
        # 加载配置文件
        self.config = load_config()
        self.ctx = AppContext(self.config)
        self.output_dir = Path(self.config.get("STORAGE", {}).get("LOCAL", {}).get("DATA_DIR", "output"))
        self.analysis_file = self.output_dir / "analysis" / "custom_analysis.json"
        self.analysis_file.parent.mkdir(parents=True, exist_ok=True)
    
    def has_analyzed_today(self):
        """检查今天是否已经分析过"""
        if not self.analysis_file.exists():
            return False
        
        try:
            with open(self.analysis_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            last_analysis = data.get('last_analysis', '')
            if not last_analysis:
                return False
            
            last_date = datetime.datetime.fromisoformat(last_analysis).date()
            today = datetime.datetime.now().date()
            return last_date == today
        except Exception:
            return False
    
    def get_today_data(self):
        """获取今天的数据"""
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        news_db = self.output_dir / "news" / f"{today}.db"
        rss_db = self.output_dir / "rss" / f"{today}.db"
        
        all_content = []
        
        # 读取新闻数据
        if news_db.exists():
            print(f"[自定义分析] 找到新闻数据库: {news_db}")
            try:
                conn = sqlite3.connect(news_db)
                cursor = conn.cursor()
                
                # 查看数据库中的表
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = cursor.fetchall()
                print(f"[自定义分析] 新闻数据库表: {tables}")
                
                # 尝试不同的表名
                tables_to_try = ["news_items", "titles", "news", "items"]
                found_table = False
                
                for table in tables_to_try:
                    try:
                        cursor.execute(f"SELECT * FROM {table} LIMIT 1")
                        columns = [description[0] for description in cursor.description]
                        print(f"[自定义分析] 表 {table} 的列: {columns}")
                        found_table = True
                        
                        # 根据表结构读取数据
                        if "title" in columns:
                            if "source_name" in columns:
                                cursor.execute(f"SELECT title, source_name FROM {table}")
                                for row in cursor.fetchall():
                                    title = row[0]
                                    source = row[1]
                                    all_content.append(f"[{source}] {title}")
                            else:
                                cursor.execute(f"SELECT title FROM {table}")
                                for row in cursor.fetchall():
                                    title = row[0]
                                    all_content.append(f"{title}")
                        break
                    except Exception as e:
                        print(f"[自定义分析] 尝试表 {table} 失败: {e}")
                
                conn.close()
            except Exception as e:
                print(f"[自定义分析] 读取新闻数据失败: {e}")
        else:
            print(f"[自定义分析] 未找到新闻数据库: {news_db}")
        
        # 读取RSS数据
        if rss_db.exists():
            print(f"[自定义分析] 找到RSS数据库: {rss_db}")
            try:
                conn = sqlite3.connect(rss_db)
                cursor = conn.cursor()
                
                # 查看数据库中的表
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = cursor.fetchall()
                print(f"[自定义分析] RSS数据库表: {tables}")
                
                # 尝试不同的表名
                tables_to_try = ["rss_items", "items", "titles"]
                found_table = False
                
                for table in tables_to_try:
                    try:
                        cursor.execute(f"SELECT * FROM {table} LIMIT 1")
                        columns = [description[0] for description in cursor.description]
                        print(f"[自定义分析] 表 {table} 的列: {columns}")
                        found_table = True
                        
                        # 根据表结构读取数据
                        if "title" in columns:
                            if "feed_name" in columns:
                                cursor.execute(f"SELECT title, feed_name FROM {table}")
                                for row in cursor.fetchall():
                                    title = row[0]
                                    feed = row[1]
                                    all_content.append(f"[{feed}] {title}")
                            else:
                                cursor.execute(f"SELECT title FROM {table}")
                                for row in cursor.fetchall():
                                    title = row[0]
                                    all_content.append(f"{title}")
                        break
                    except Exception as e:
                        print(f"[自定义分析] 尝试表 {table} 失败: {e}")
                
                conn.close()
            except Exception as e:
                print(f"[自定义分析] 读取RSS数据失败: {e}")
        else:
            print(f"[自定义分析] 未找到RSS数据库: {rss_db}")
        
        print(f"[自定义分析] 总共收集到 {len(all_content)} 条内容")
        return all_content
    
    def analyze(self):
        """执行分析"""
        # 检查今天是否已经分析过
        if self.has_analyzed_today():
            print("[自定义分析] 今天已经分析过，跳过本次分析")
            return None
        
        # 获取今天的数据
        content = self.get_today_data()
        if not content:
            print("[自定义分析] 没有找到今天的数据")
            return None
        
        print(f"[自定义分析] 找到 {len(content)} 条内容")
        
        # 准备AI分析
        ai_config = self.ctx.config.get("AI", {})
        analysis_config = {
            "ENABLED": True,
            "MODE": "daily",
            "MAX_NEWS_FOR_ANALYSIS": 100
        }
        
        analyzer = AIAnalyzer(ai_config, analysis_config, self.ctx.get_time)
        
        # 构建分析提示词
        prompt_file = Path(__file__).parent / "prompt.txt"
        if prompt_file.exists():
            with open(prompt_file, 'r', encoding='utf-8') as f:
                system_prompt = f.read().strip()
            print("[自定义分析] 使用自定义提示词")
        else:
            # 默认提示词
            system_prompt = """
你是一位专业的分析专家，请基于提供的热点新闻数据进行分析。

请关注：
1. 国际局势相关
2. 中国大事相关
3. 影响较大的社会新闻

请直接输出分析结果，不需要特定格式。
            """
            print("[自定义分析] 使用默认提示词")
        
        # 构建用户提示词
        content_str = "\n".join(content[:100])  # 限制数量，避免token超限
        user_prompt = f"""
请基于以下热点新闻数据进行分析：

{content_str}

请直接输出分析结果。
        """
        
        # 执行AI分析
        try:
            # 临时修改系统提示词
            original_system_prompt = analyzer.system_prompt
            analyzer.system_prompt = system_prompt
            
            # 构建模拟的stats数据
            stats = [{
                "word": "自定义分析",
                "titles": [{
                    "title": "分析热点新闻",
                    "source_name": "系统"
                }]
            }]
            
            # 执行分析
            result = analyzer.analyze(
                stats=stats,
                report_mode="daily",
                report_type="自定义分析",
                platforms=["系统"]
            )
            
            # 恢复原始系统提示词
            analyzer.system_prompt = original_system_prompt
            
            if result.success:
                # 保存分析结果（简化版本）
                analysis_data = {
                    "last_analysis": datetime.datetime.now().isoformat(),
                    "result": {
                        "full_analysis": result.core_trends
                    }
                }
                
                with open(self.analysis_file, 'w', encoding='utf-8') as f:
                    json.dump(analysis_data, f, ensure_ascii=False, indent=2)
                
                print("[自定义分析] 分析完成并保存结果")
                return analysis_data
            else:
                print(f"[自定义分析] 分析失败: {result.error}")
                return None
        except Exception as e:
            print(f"[自定义分析] 分析出错: {e}")
            traceback.print_exc()
            return None
    
    def generate_standalone_data(self):
        """生成独立展示区数据（极简版本）"""
        if not self.analysis_file.exists():
            print("[自定义分析] 没有找到分析结果")
            return None
        
        try:
            with open(self.analysis_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            result = data.get('result', {})
            if not result:
                return None
            
            # 构建极简的独立展示区数据
            standalone_data = {
                "platforms": [
                    {
                        "platform_id": "custom_analysis",
                        "platform_name": "自定义分析",
                        "titles": []
                    }
                ],
                "rss_feeds": []
            }
            
            # 直接添加AI分析的原始结果
            if result:
                # 检查是否有full_analysis字段（简化分析结果）
                if "full_analysis" in result:
                    analysis_text = result["full_analysis"]
                else:
                    # 兼容旧格式
                    analysis_text = "\n\n".join([
                        result.get('core_trends', ''),
                        result.get('sentiment_controversy', ''),
                        result.get('outlook_strategy', '')
                    ])
                
                standalone_data["platforms"][0]["titles"].append({
                    "title": analysis_text,
                    "time_display": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "rank": 1
                })
            
            return standalone_data
        except Exception as e:
            print(f"[自定义分析] 生成独立展示区数据出错: {e}")
            return None
    
    def push_analysis(self):
        """推送分析结果"""
        # 执行分析
        analysis_data = self.analyze()
        if not analysis_data:
            # 如果今天已经分析过，直接生成展示数据
            standalone_data = self.generate_standalone_data()
        else:
            standalone_data = self.generate_standalone_data()
        
        if not standalone_data:
            print("[自定义分析] 没有可推送的分析结果")
            return False
        
        # 创建通知调度器
        dispatcher = self.ctx.create_notification_dispatcher()
        
        # 构建报告数据
        report_data = {
            "stats": [],
            "failed_ids": [],
            "new_titles": {},
            "id_to_name": {}
        }
        
        # 发送推送
        try:
            results = dispatcher.dispatch_all(
                report_data=report_data,
                report_type="公众号写作方向分析",
                mode="daily",
                standalone_data=standalone_data
            )
            print(f"[自定义分析] 推送结果: {results}")
            return True
        except Exception as e:
            print(f"[自定义分析] 推送出错: {e}")
            return False

if __name__ == "__main__":
    analyzer = CustomAnalyzer()
    analyzer.push_analysis()
