import os
import polars as pl
import matplotlib.pyplot as plt
from dune_client.client import DuneClient

# ==========================================
# 1. 配置区域
# ==========================================
DUNE_API_KEY = "yOBqrXxcE9rjIM9h4UhxvGDHwOSlsyDO" 
OUTPUT_DIR = "data/raw"
PLOT_DIR = "results"
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(PLOT_DIR, exist_ok=True)

def fetch_and_process():
    # 2. 定义 SQL (保持不变)
    query_sql = """
    WITH usdc_burns AS (
        SELECT 
            evt_block_time,
            evt_tx_hash,
            "from" AS user_address,
            value / 1e6 AS amount_usdc
        FROM erc20_ethereum.evt_Transfer
        WHERE contract_address = 0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48
        AND "to" = 0x0000000000000000000000000000000000000000
        AND evt_block_time BETWEEN CAST('2024-08-04 00:00:00' AS TIMESTAMP) 
                               AND CAST('2024-08-06 00:00:00' AS TIMESTAMP)
    )
    SELECT 
        b.evt_block_time,
        b.evt_tx_hash,
        b.user_address,
        b.amount_usdc,
        t.gas_price / 1e9 AS gas_price_gwei,
        (t.gas_price * t.gas_used) / 1e18 AS tx_fee_eth
    FROM usdc_burns b
    INNER JOIN ethereum.transactions t 
        ON b.evt_tx_hash = t.hash
        AND t.block_time BETWEEN CAST('2024-08-04 00:00:00' AS TIMESTAMP) 
                             AND CAST('2024-08-06 00:00:00' AS TIMESTAMP)
    """

    print("🚀 正在请求 Dune Data (48h Vertical Slice)...")
    client = DuneClient(DUNE_API_KEY)
    
    try:
        results = client.run_sql(query_sql)
        raw_rows = results.result.rows
        print(f"✅ 成功抓取 {len(raw_rows)} 条记录")
    except Exception as e:
        print(f"❌ API 请求失败: {e}")
        return

    # ==========================================
    # 3. Polars 核心修正：显式定义时间格式
    # ==========================================
    # Dune 格式: "2024-08-05 06:09:35.000 UTC"
    # 对应模式: "%Y-%m-%d %H:%M:%S%.3f UTC"
    df = pl.DataFrame(raw_rows).with_columns([
        pl.col("amount_usdc").cast(pl.Float64),
        pl.col("gas_price_gwei").cast(pl.Float64),
        pl.col("tx_fee_eth").cast(pl.Float64),
        # 修正点：使用精确匹配并显式设置时区
        pl.col("evt_block_time")
          .str.to_datetime(format="%Y-%m-%d %H:%M:%S%.3f UTC")
          .dt.replace_time_zone("UTC")
    ]).sort("evt_block_time")

    # 4. 存储数据
    parquet_path = os.path.join(OUTPUT_DIR, "usdc_burns_48h.parquet")
    df.write_parquet(parquet_path)
    print(f"💾 数据已清洗并存至: {parquet_path}")

    # ==========================================
    # 5. 可视化：Gas 压力响应分析
    # ==========================================
    print("📈 生成可视化分析中...")
    
    # 5分钟窗口聚合
    df_resampled = df.group_by_dynamic(
        "evt_block_time", every="5m"
    ).agg([
        pl.col("amount_usdc").sum().alias("total_burn_volume"),
        pl.col("gas_price_gwei").mean().alias("avg_gas_price")
    ])

    fig, ax1 = plt.subplots(figsize=(14, 7))

    # 左轴：Gas Price
    color_gas = '#e74c3c'
    ax1.set_xlabel('Time (UTC)')
    ax1.set_ylabel('Avg Gas Price (Gwei)', color=color_gas, fontweight='bold')
    ax1.plot(df_resampled["evt_block_time"], df_resampled["avg_gas_price"], 
             color=color_gas, linewidth=1.5, label='Gas Price (Stress)')
    ax1.tick_params(axis='y', labelcolor=color_gas)
    ax1.grid(True, linestyle='--', alpha=0.5)

    # 右轴：Burn Volume
    ax2 = ax1.twinx()
    color_vol = '#3498db'
    ax2.set_ylabel('USDC Redemption Volume ($)', color=color_vol, fontweight='bold')
    ax2.fill_between(df_resampled["evt_block_time"], df_resampled["total_burn_volume"], 
                     color=color_vol, alpha=0.4, label='USDC Burn Volume')
    ax2.tick_params(axis='y', labelcolor=color_vol)

    plt.title("USDC Stress Response: Price Elasticity Observation", fontsize=14)
    fig.tight_layout()
    
    plot_path = os.path.join(PLOT_DIR, "gas_stress_analysis.png")
    plt.savefig(plot_path, dpi=300) # 保持高分辨率用于论文插图
    print(f"🖼️ 图表已保存至: {plot_path}")
    plt.show()

if __name__ == "__main__":
    fetch_and_process()