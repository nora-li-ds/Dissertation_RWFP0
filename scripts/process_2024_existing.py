from pathlib import Path
import polars as pl

ROOT = Path.cwd().parent if Path.cwd().name == "scripts" else Path.cwd()

RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed_2024"
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

files = sorted(RAW_DIR.glob("dune_hourly_2024-*.parquet"))

if not files:
    raise FileNotFoundError(f"No 2024 parquet files found in {RAW_DIR}")

print(f"Found {len(files)} files.")

frames = []
for f in files:
    print(f"Loading {f.name}")
    frames.append(pl.read_parquet(f))

df = pl.concat(frames, how="vertical")

print("Raw rows:", df.height)
print("Schema before:")
print(df.schema)

# Robust time parsing
if df.schema["time"] == pl.Utf8:
    df = df.with_columns(
        pl.col("time")
        .str.replace(" UTC", "+00:00")
        .str.to_datetime(format="%Y-%m-%d %H:%M:%S%.3f%z", strict=False)
        .alias("time")
    )

if isinstance(df.schema["time"], pl.Datetime):
    df = df.with_columns(
        pl.col("time").dt.replace_time_zone(None).alias("time")
    )

df = (
    df
    .with_columns([
        pl.col("cashout_volume_usd").cast(pl.Float64),
        pl.col("transfer_count").cast(pl.Int64),
        pl.col("avg_gas_gwei").cast(pl.Float64),
    ])
    .sort("time")
    .drop_nulls(subset=["avg_gas_gwei"])
)

gas_threshold = df.select(
    pl.col("avg_gas_gwei").quantile(0.90)
).item()

print(f"2024 gas shock threshold, 90th percentile: {gas_threshold:.2f} Gwei")

df = df.with_columns([
    (pl.col("avg_gas_gwei") >= gas_threshold).cast(pl.Int8).alias("shock"),
    (pl.col("cashout_volume_usd") + 1).log().alias("log_volume"),
    (pl.col("avg_gas_gwei") + 1).log().alias("log_gas"),
])

csv_path = PROCESSED_DIR / "dune_stablecoin_cex_hourly.csv"
parquet_path = PROCESSED_DIR / "dune_stablecoin_cex_hourly.parquet"

df.write_csv(csv_path)
df.write_parquet(parquet_path)

print("Saved:")
print(csv_path)
print(parquet_path)

print(df.head(10))