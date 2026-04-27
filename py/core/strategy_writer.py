# coding=utf-8
"""生成 Markdown 策略文件（修复阶段匹配与执行清单）"""
from datetime import datetime, timedelta

def generate_strategy(data, anchor, main_lines, main_msg, mname, mstage):
    date_str = data['date']
    next_date = (datetime.strptime(date_str, '%Y%m%d') + timedelta(days=1)).strftime('%Y%m%d')

    total_amt = data.get('sh_amount', 0) + data.get('sz_amount', 0)
    sh = data.get('sh_index', 0)
    m20 = data.get('ma20', 0)
    mlb = data.get('max_lianban', 0)

    # 环境等级
    if sh > m20 and total_amt > 22000 and mlb > 5:
        env, max_cang = 'S', 4
    elif sh > m20 and total_amt >= 15000:
        env, max_cang = 'A', 3
    else:
        env, max_cang = 'B', 2

    lines = []
    lines.append(f"# 豆包模式 · 自动盘前策略（{date_str} 复盘 -> {next_date}）")
    lines.append(f"\n> **环境等级**：{env}级 | 总仓位上限：仓{max_cang} | 生成时间：{datetime.now().strftime('%H:%M:%S')}")
    lines.append("")
    lines.append("## 1. 大盘状态")
    lines.append(f"- 上证：{sh:.2f}（{data.get('sh_pct', 0):+.2f}%），成交{data.get('sh_amount', 0):.0f}亿")
    lines.append(f"- 两市成交：{total_amt:.0f}亿")
    if 'up_count' in data:
        lines.append(f"- 涨跌家数：{data['up_count']}涨 / {data['down_count']}跌")
    lines.append(f"- 20日线：{m20:.2f}（{'站上' if sh > m20 else '跌破'}）")
    lines.append("")
    lines.append("## 2. 情绪周期")
    lines.append(f"- 涨停{data.get('limit_total', 0)} | 跌停{data.get('dieting_total', 0)} | 炸板{data.get('zhaban_total', 0)}")
    lines.append(f"- 最高连板：{mlb}连板")

    from config_loader import load_config
    cfg = load_config()
    holdings = cfg.get('current_holdings', {})
    if holdings:
        lines.append("\n## 当前持仓处理")
        for s, p in holdings.items():
            if mname and mstage == 'E':
                lines.append(f"- **{s}（{p}成）：主线已退潮（E），建议清仓**")
            else:
                lines.append(f"- {s}（{p}成）：根据主线状态决定去留")
    lines.append("")
    lines.append("## 3. 主线评估与角色定位")
    lines.append(main_msg)
    for ml in main_lines:
        sym = "[OK]" if ml['score'] >= 4.5 else ("[WATCH]" if ml['score'] >= 4.0 else "[WARN]")
        lines.append(f"\n### {sym} {ml['name']}（{ml['score']}分，阶段：{ml['stage']}）")
        roles = ml.get('roles', {})
        if ml['stage'] == 'C':
            lines.append("- 启动日，等待确认（需连续3日评分≥4.5且中军走强）")
        elif 'G' in ml['stage']:
            lines.append("- 主升期，持有不加仓")
        elif 'D' in ml['stage']:
            lines.append("- 分歧期，观察活口")
        elif ml['stage'] == 'E':
            lines.append("- **退潮期，不参与**")
        else:
            lines.append("- 候选方向")
        if roles:
            mid_cap = roles.get('mid_cap', [])
            lianban = roles.get('lianban_pioneer')
            elastic = roles.get('elastic_pioneer')
            trend = roles.get('trend_pioneer')
            if mid_cap:
                parts = [f"{m['name']}(成交{m.get('amount', 0):.0f}亿)" for m in mid_cap]
                lines.append(f"- 核心中军：{', '.join(parts)}")
            if lianban:
                lines.append(f"- 连板先锋(10cm)：{lianban['name']}(封板{lianban['first_time']}，换手{lianban['turnover']}%，封单{lianban['seal_amount']:.2f}亿)")
            if elastic:
                lines.append(f"- 弹性先锋(20cm)：{elastic['name']}({elastic['pct']}%，换手{elastic['turnover']}%)")
            if trend:
                lines.append(f"- 趋势先锋：{trend['name']}(趋势评分{trend.get('trend_score', 0):.1f}，量比{trend.get('lb', 1):.1f})")

    lines.append("\n## 4. 明日执行清单")
    lines.append(f"- 总仓位上限：{max_cang * 10}%")
    has_buy = False
    for ml in main_lines:
        stage = ml['stage']
        # C日 → 等待确认
        if stage == 'C' and ml.get('type') == 'main':
            lines.append(f"\n### {ml['name']}（C日->等待确认）")
            lines.append("- 确认信号：核心封单加大≥50%且>3亿，新增涨停≥2家，板块收涨>2%")
            lines.append("- 确认即执行买点C类型B，仓位仓3-仓4")
            has_buy = True
        # 1G-1 / 2G-1 / 3G-1 → 弱转强确认日
        elif stage in ('1G-1', '2G-1', '3G-1') and ml.get('type') == 'main':
            lines.append(f"\n### {ml['name']}（弱转强确认日）")
            lines.append("- 可执行D2/D3买点，仓位仓2-仓3")
            roles = ml.get('roles', {})
            lianban = roles.get('lianban_pioneer')
            elastic = roles.get('elastic_pioneer')
            mid_cap = roles.get('mid_cap', [])
            trend = roles.get('trend_pioneer')
            if lianban:
                lines.append(f"  - **D2买点（连板先锋）**：{lianban['name']} 竞价高开3-7%+竞价放量→跟随买入")
            if elastic:
                lines.append(f"  - **弹性套利（20cm）**：{elastic['name']} 若先锋买不到，板块确认后沿分时均线低吸")
            if trend:
                lines.append(f"  - **趋势低吸**：{trend['name']} 趋势评分{trend.get('trend_score',0):.1f}，回踩5日线缩量可低吸")
            if mid_cap:
                names = [m['name'] for m in mid_cap]
                lines.append(f"  - **D3买点（中军低吸）**：{', '.join(names)} 回踩5日线缩量企稳→尾盘或次日早盘低吸")
            has_buy = True
        # 其他G阶段（1G-2, 2G-2 等）→ 持有，不加仓
        elif 'G' in stage and ml.get('type') == 'main':
            lines.append(f"\n### {ml['name']}（{stage}，主升持有）")
            lines.append("- 已持仓者继续持有，不加仓")
            lines.append("- 未持仓者等待分歧日（D阶段）再找买点")
            has_buy = True
    if not has_buy:
        lines.append("\n**执行清单为空**（无符合买点的方向，继续观察）")

    lines.append("\n---")
    lines.append(f"*本策略由豆包模式自动生成 v6.0 模块化*")
    return '\n'.join(lines)