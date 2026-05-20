# --- 修改后的深度智能分析引擎（增加了 core_metric 参数） ---
def run_deep_analysis(df, core_metric):
    st.header("🧠 深度智能分析报告")
    
    # 自动识别分类列（用于漏斗匹配等）
    categorical_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
    
    if not core_metric:
        st.warning("⚠️ 请在侧边栏选择一个核心数值指标进行分析。")
        return

    # --- 核心指标计算 ---
    # 计算转化率链条（依然尝试自动匹配漏斗字段）
    funnel_steps = []
    potential_steps = ['AI接通数', '人工接通数', '有效接通数']
    
    # 构建漏斗数据字典，以用户选的核心指标为起点
    funnel_data = {core_metric: df[core_metric].sum()}
    
    current_val = df[core_metric].sum()
    for step in potential_steps:
        if step in df.columns:
            val = df[step].sum()
            funnel_data[step] = val
            # 计算上一步到这一步的转化率（防止除以0）
            if current_val > 0:
                rate = (val / current_val) * 100
                funnel_steps.append((step, val, rate))
            current_val = val if val > 0 else current_val 

    # --- 生成文字报告 ---
    st.subheader("📝 核心结论摘要")
    
    report_text = []
    
    # 1. 总量分析
    report_text.append(f"### 1. 业务规模概览")
    report_text.append(f"本次统计周期内，核心指标 **《{core_metric}》** 总量达到 **{funnel_data[core_metric]:,.0f}**。")
    
    # 2. 转化漏斗分析
    if funnel_steps:
        report_text.append(f"### 2. 转化效率分析")
        best_step_name, best_step_val, best_rate = max(funnel_steps, key=lambda x: x[2])
        worst_step_name, worst_step_val, worst_rate = min(funnel_steps, key=lambda x: x[2])
        
        report_text.append(f"- **整体流转情况**：从 `{core_metric}` 开始，数据经过层层筛选。")
        report_text.append(f"- **表现最佳环节**：**【{best_step_name}】** 环节转化率最高，达到 **{best_rate:.1f}%**。")
        report_text.append(f"- **需关注瓶颈**：**【{worst_step_name}】** 环节转化率最低（**{worst_rate:.1f}%**），建议重点排查。")
        
        # 具体的流失数字
        steps_with_total = [(core_metric, funnel_data[core_metric])] + [(name, val) for name, val, _ in funnel_steps]
        for i in range(len(steps_with_total)-1):
            curr_name, curr_val = steps_with_total[i]
            next_name, next_val = steps_with_total[i+1]
            loss = curr_val - next_val
            if loss > 0:
                report_text.append(f"- *细节：从 `{curr_name}` 到 `{next_name}` 流失了约 **{loss:,.0f}** 条数据。*")
    else:
        report_text.append("### 2. 转化效率分析\n- 未检测到标准的转化漏斗字段，跳过漏斗分析。")

    # 3. 波动性/稳定性分析
    report_text.append(f"### 3. 数据稳定性分析")
    std_dev = df[core_metric].std()
    mean_val = df[core_metric].mean()
    cv = (std_dev / mean_val) * 100 if mean_val != 0 else 0
    
    stability_status = "⚠️ 波动较大" if cv > 50 else "✅ 相对稳定"
    report_text.append(f"- 核心指标 **{core_metric}** 的样本均值为 **{mean_val:,.0f}**，标准差为 **{std_dev:,.0f}**。")
    report_text.append(f"- 变异系数(CV)为 **{cv:.1f}%**，表明近期数据表现 **{stability_status}**。")

    # 渲染报告
    final_report = "\n\n".join(report_text)
    st.markdown(final_report)

    # --- 可视化：自动漏斗图 ---
    if funnel_steps:
        st.divider()
        st.subheader("📉 转化漏斗可视化")
        
        funnel_df = pd.DataFrame(list(funnel_data.items()), columns=['Stage', 'Count'])
        
        fig = go.Figure(go.Funnel(
            y = funnel_df['Stage'],
            x = funnel_df['Count'],
            textinfo = "value+percent initial",
            marker = {"color": px.colors.sequential.Viridis}
        ))
        fig.update_layout(height=400, margin=dict(l=50, r=50, t=50, b=50))
        st.plotly_chart(fig, use_container_width=True)


# --- 修改后的主程序 ---
def main():
    st.title("📊 深度智能数据分析看板")
    
    # 侧边栏
    with st.sidebar:
        st.header("🛠️ 数据配置")
        uploaded_file = st.file_uploader("上传 Excel 文件", type=['xlsx', 'xls'])
        
        # 新增：核心指标选择器
        if uploaded_file:
            df_temp = load_data(uploaded_file)
            if df_temp is not None:
                numeric_cols = df_temp.select_dtypes(include=['number']).columns.tolist()
                if numeric_cols:
                    st.subheader("🎯 核心指标设定")
                    core_metric = st.selectbox("请选择本次分析的核心指标", numeric_cols)
                else:
                    core_metric = None
                    st.warning("未找到数值列")
            else:
                core_metric = None
        else:
            core_metric = None
        
    if uploaded_file:
        df = load_data(uploaded_file)
        if df is not None and not df.empty:
            # 数据预览
            with st.expander("查看原始数据", expanded=False):
                st.dataframe(df, use_container_width=True)
            
            # 运行深度分析（传入用户选择的核心指标）
            run_deep_analysis(df, core_metric)
            
            st.divider()
            
            # --- 自定义图表分析（保持原有逻辑） ---
            st.header("📈 自定义图表分析")
            numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
            all_cols = df.columns.tolist()
            
            if not numeric_cols:
                st.info("当前数据没有数值列，无法生成图表。")
            else:
                chart_type = st.selectbox("选择图表类型 (自动/手动)", ["自动推荐", "柱状图", "折线图", "散点图", "饼图"])
                
                col1, col2 = st.columns(2)
                with col1:
                    x_axis = st.selectbox("选择 X 轴", all_cols, index=0)
                with col2:
                    y_index = all_cols.index(numeric_cols[0]) if numeric_cols[0] in all_cols else 0
                    y_axis = st.selectbox("选择 Y 轴 (数值)", all_cols, index=y_index)
                    
                if st.button("生成图表"):
                    if x_axis and y_axis:
                        rec_type = get_chart_config(df[x_axis], df[y_axis])
                        final_type = chart_type if chart_type != "自动推荐" else rec_type
                        
                        fig = None
                        try:
                            if final_type == "bar":
                                fig = px.bar(df, x=x_axis, y=y_axis, title=f"{y_axis} by {x_axis}")
                            elif final_type == "line":
                                fig = px.line(df, x=x_axis, y=y_axis, title=f"{y_axis} Trend")
                            elif final_type == "scatter":
                                fig = px.scatter(df, x=x_axis, y=y_axis, title=f"{y_axis} vs {x_axis}")
                            elif final_type == "pie":
                                fig = px.pie(df, names=x_axis, values=y_axis, title=f"{y_axis} Distribution")
                            
                            if fig:
                                st.plotly_chart(fig, use_container_width=True)
                        except Exception as e:
                            st.error(f"图表生成失败，请检查字段类型是否匹配。错误信息: {e}")

if __name__ == "__main__":
    main()
