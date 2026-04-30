# ============================================================
# SECU0069 Analysis: Stablecoin Transfer Volume and Gas Fees
# ARIMAX / Time-Series Pilot Analysis
# ============================================================

# 1. Load packages --------------------------------------------------------

install.packages("tseries", repos = "https://cran.ma.imperial.ac.uk")
install.packages('broom', repos='https://cran.ma.imperial.ac.uk')
required_packages <- c(
  "tidyverse",
  "lubridate",
  "forecast",
  "tseries",
  "broom",
  "knitr"
)

for (pkg in required_packages) {
  if (!require(pkg, character.only = TRUE)) {
    install.packages(pkg)
    library(pkg, character.only = TRUE)
  }
}

# 2. Set paths ------------------------------------------------------------

root <- normalizePath(file.path(getwd()))

# If running from scripts folder, move one level up
if (basename(root) == "scripts") {
  root <- normalizePath(file.path(root, ".."))
}

data_path <- file.path(
  root,
  "data",
  "processed_2026",
  "dune_stablecoin_cex_hourly.csv"
)

results_dir <- file.path(root, "results_2026")
if (!dir.exists(results_dir)) {
  dir.create(results_dir, recursive = TRUE)
}

# 3. Load data ------------------------------------------------------------

df <- read_csv(data_path, show_col_types = FALSE)

df <- df %>%
  mutate(
    time = parse_date_time(
      time,
      orders = c(
        "ymd HMS",
        "ymd HM",
        "ymd HMS OS",
        "ymd HM OS",
        "ymd"
      ),
      tz = "UTC"
    ),
    cashout_volume_usd = as.numeric(cashout_volume_usd),
    transfer_count = as.numeric(transfer_count),
    avg_gas_gwei = as.numeric(avg_gas_gwei),
    shock = as.factor(shock),
    log_volume = log(cashout_volume_usd + 1),
    log_gas = log(avg_gas_gwei + 1),
    time_index = row_number()
  ) %>%
  arrange(time)

cat("\nData loaded successfully.\n")
cat("Number of rows:", nrow(df), "\n")
cat(
  "Time range:",
  as.character(min(df$time, na.rm = TRUE)),
  "to",
  as.character(max(df$time, na.rm = TRUE)),
  "\n"
)

cat("Rows with failed time parsing:", sum(is.na(df$time)), "\n")

# 4. Descriptive statistics ----------------------------------------------

desc_stats <- df %>%
  summarise(
    n = n(),
    mean_volume = mean(cashout_volume_usd, na.rm = TRUE),
    sd_volume = sd(cashout_volume_usd, na.rm = TRUE),
    min_volume = min(cashout_volume_usd, na.rm = TRUE),
    max_volume = max(cashout_volume_usd, na.rm = TRUE),
    mean_gas = mean(avg_gas_gwei, na.rm = TRUE),
    sd_gas = sd(avg_gas_gwei, na.rm = TRUE),
    min_gas = min(avg_gas_gwei, na.rm = TRUE),
    max_gas = max(avg_gas_gwei, na.rm = TRUE),
    shock_hours = sum(as.numeric(as.character(shock)) == 1, na.rm = TRUE)
  )

print(desc_stats)

write_csv(desc_stats, file.path(results_dir, "descriptive_statistics.csv"))

# 5. Plot time series -----------------------------------------------------

p1 <- ggplot(df, aes(x = time)) +
  geom_line(aes(y = avg_gas_gwei)) +
  labs(
    title = "Hourly Ethereum Gas Fee",
    x = "Time",
    y = "Average gas fee (Gwei)"
  ) +
  theme_minimal()

ggsave(
  filename = file.path(results_dir, "hourly_gas_fee.png"),
  plot = p1,
  width = 10,
  height = 5,
  dpi = 300
)

p2 <- ggplot(df, aes(x = time)) +
  geom_line(aes(y = cashout_volume_usd)) +
  labs(
    title = "Hourly Stablecoin Transfers to Dune-labelled CEX Users",
    x = "Time",
    y = "Transfer volume, USD"
  ) +
  theme_minimal()

ggsave(
  filename = file.path(results_dir, "hourly_cashout_volume.png"),
  plot = p2,
  width = 10,
  height = 5,
  dpi = 300
)

# 6. Simple OLS baseline --------------------------------------------------

m1 <- lm(
  log_volume ~ log_gas + shock + time_index,
  data = df
)

cat("\n================ OLS model ================\n")
print(summary(m1))

m1_table <- broom::tidy(m1)
write_csv(m1_table, file.path(results_dir, "ols_model_results.csv"))

# 7. Check autocorrelation ------------------------------------------------

acf_png <- file.path(results_dir, "acf_log_volume.png")
png(acf_png, width = 900, height = 600)
acf(df$log_volume, main = "ACF of log stablecoin transfer volume")
dev.off()

cat("\nACF plot saved to:", acf_png, "\n")

# 8. ARIMAX model ---------------------------------------------------------

# For ARIMAX, shock should be numeric not factor
df <- df %>%
  mutate(
    shock_numeric = as.numeric(as.character(shock))
  )

xreg <- as.matrix(df %>% select(log_gas, shock_numeric))

m2 <- auto.arima(
  df$log_volume,
  xreg = xreg,
  seasonal = FALSE,
  stepwise = FALSE,
  approximation = FALSE
)

cat("\n================ ARIMAX model ================\n")
print(summary(m2))

# Save ARIMAX coefficients
m2_coef <- data.frame(
  term = names(coef(m2)),
  estimate = as.numeric(coef(m2))
)

write_csv(m2_coef, file.path(results_dir, "arimax_coefficients.csv"))

# 9. Residual diagnostics -------------------------------------------------

resid_png <- file.path(results_dir, "arimax_residuals.png")
png(resid_png, width = 900, height = 600)
checkresiduals(m2)
dev.off()

cat("\nARIMAX residual diagnostics saved to:", resid_png, "\n")

# 10. Forecast-style fitted values plot ----------------------------------

fitted_values <- fitted(m2)

df_plot <- df %>%
  mutate(
    fitted_log_volume = as.numeric(fitted_values)
  )

p3 <- ggplot(df_plot, aes(x = time)) +
  geom_line(aes(y = log_volume), linewidth = 0.4) +
  geom_line(aes(y = fitted_log_volume), linewidth = 0.4, linetype = "dashed") +
  labs(
    title = "Observed vs Fitted Log Stablecoin Transfer Volume",
    x = "Time",
    y = "Log transfer volume"
  ) +
  theme_minimal()

ggsave(
  filename = file.path(results_dir, "observed_vs_fitted_arimax.png"),
  plot = p3,
  width = 10,
  height = 5,
  dpi = 300
)

cat("\nAnalysis complete. Results saved to:\n")
cat(results_dir, "\n")