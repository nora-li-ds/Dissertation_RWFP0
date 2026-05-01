# SECU0069 report analysis
# Candidate ID: RWFP0
#
# This script runs the statistical analysis used in my report.
# It uses the processed hourly Dune datasets for:
#   1. August 2024, a higher-fee comparison period
#   2. March-April 2026, a recent low-fee comparison period
#
# The Python scripts used to collect and preprocess the Dune data are documented here:
# https://github.com/nora-li-ds/Gas-Stress-Test-AML
#
# API keys and raw credentials are not included.

# Load packages

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
    install.packages(pkg, repos = "https://cran.ma.imperial.ac.uk")
    library(pkg, character.only = TRUE)
  }
}

# Set paths
root <- normalizePath(getwd())

# This allows the script to run either from the project root or from scripts/.
if (basename(root) == "scripts") {
  root <- normalizePath(file.path(root, ".."))
}

results_dir <- file.path(root, "results_two_periods")

if (!dir.exists(results_dir)) {
  dir.create(results_dir, recursive = TRUE)
}

path_2024 <- file.path(
  root,
  "data",
  "processed_2024",
  "dune_stablecoin_cex_hourly.csv"
)

path_2026 <- file.path(
  root,
  "data",
  "processed_2026",
  "dune_stablecoin_cex_hourly.csv"
)

# Helper function to load each period

load_period <- function(path, period_name) {
  df <- read_csv(path, show_col_types = FALSE) %>%
    mutate(
      # Some midnight rows may be stored as date-only values, so I allow several formats.
      time = parse_date_time(
        time,
        orders = c("ymd HMS", "ymd HM", "ymd HMS OS", "ymd HM OS", "ymd"),
        tz = "UTC"
      ),
      cashout_volume_usd = as.numeric(cashout_volume_usd),
      transfer_count = as.numeric(transfer_count),
      avg_gas_gwei = as.numeric(avg_gas_gwei),
      shock = as.numeric(shock),

      # Log variables are used because both volume and gas fees are highly skewed.
      log_volume = log(cashout_volume_usd + 1),
      log_gas = log(avg_gas_gwei + 1),
      period = period_name
    ) %>%
    arrange(time) %>%
    mutate(time_index = row_number())

  cat("\nLoaded", period_name, "\n")
  cat("Rows:", nrow(df), "\n")
  cat("Failed time parsing:", sum(is.na(df$time)), "\n")
  cat(
    "Time range:",
    as.character(min(df$time, na.rm = TRUE)),
    "to",
    as.character(max(df$time, na.rm = TRUE)),
    "\n"
  )
  cat("Mean gas:", mean(df$avg_gas_gwei, na.rm = TRUE), "\n")
  cat("Max gas:", max(df$avg_gas_gwei, na.rm = TRUE), "\n")
  cat("Shock hours:", sum(df$shock == 1, na.rm = TRUE), "\n")

  df
}

df_2024 <- load_period(path_2024, "high_fee_2024")
df_2026 <- load_period(path_2026, "low_fee_2026")

# Descriptive comparison 
# This table is used to show that the two periods are genuinely different
# fee environments.
desc <- bind_rows(df_2024, df_2026) %>%
  group_by(period) %>%
  summarise(
    n = n(),
    mean_volume = mean(cashout_volume_usd, na.rm = TRUE),
    sd_volume = sd(cashout_volume_usd, na.rm = TRUE),
    min_volume = min(cashout_volume_usd, na.rm = TRUE),
    max_volume = max(cashout_volume_usd, na.rm = TRUE),
    mean_gas = mean(avg_gas_gwei, na.rm = TRUE),
    sd_gas = sd(avg_gas_gwei, na.rm = TRUE),
    min_gas = min(avg_gas_gwei, na.rm = TRUE),
    p90_gas = quantile(avg_gas_gwei, 0.90, na.rm = TRUE),
    max_gas = max(avg_gas_gwei, na.rm = TRUE),
    shock_hours = sum(shock == 1, na.rm = TRUE)
  )

print(desc)
write_csv(desc, file.path(results_dir, "two_period_descriptive_statistics.csv"))

# ARIMAX models
run_arimax <- function(df, period_name) {
  df <- df %>%
    filter(!is.na(log_volume), !is.na(log_gas), !is.na(shock))

  # log_gas and shock are included as external regressors.
  xreg <- as.matrix(df %>% select(log_gas, shock))

  # I use auto.arima to select the ARIMA error structure for each period.
  model <- auto.arima(
    df$log_volume,
    xreg = xreg,
    seasonal = FALSE,
    stepwise = FALSE,
    approximation = FALSE
  )

  cat("\n================ ARIMAX:", period_name, "================\n")
  print(summary(model))

  coef_table <- data.frame(
    period = period_name,
    term = names(coef(model)),
    estimate = as.numeric(coef(model)),
    se = sqrt(diag(model$var.coef))
  ) %>%
    mutate(t_value = estimate / se)

  write_csv(
    coef_table,
    file.path(results_dir, paste0("arimax_coefficients_", period_name, ".csv"))
  )

  # Residual checks are saved because serial correlation is important for this data.
  png(
    file.path(results_dir, paste0("arimax_residuals_", period_name, ".png")),
    width = 900,
    height = 600
  )
  checkresiduals(model)
  dev.off()

  model
}

m_2024 <- run_arimax(df_2024, "high_fee_2024")
m_2026 <- run_arimax(df_2026, "low_fee_2026")

# Combined interaction model
combined <- bind_rows(df_2024, df_2026) %>%
  mutate(
    period = factor(period),
    shock = as.numeric(shock),
    global_index = row_number()
  )

# This model checks whether the gas-volume relationship changes across periods.
# It is not intended as a formal DiD model, because there is no clean untreated group.
m_interaction <- lm(
  log_volume ~ log_gas * period + shock * period + global_index,
  data = combined
)

cat("\n================ Combined interaction OLS ================\n")
print(summary(m_interaction))

interaction_table <- broom::tidy(m_interaction)

write_csv(
  interaction_table,
  file.path(results_dir, "combined_interaction_ols.csv")
)

# Plots
p1 <- ggplot(combined, aes(x = time, y = avg_gas_gwei)) +
  geom_line() +
  facet_wrap(~ period, scales = "free_x") +
  labs(
    title = "Hourly gas fee by period",
    x = "Time",
    y = "Average gas fee, Gwei"
  ) +
  theme_minimal()

ggsave(
  file.path(results_dir, "gas_fee_by_period.png"),
  p1,
  width = 10,
  height = 5,
  dpi = 300
)

p2 <- ggplot(combined, aes(x = time, y = cashout_volume_usd)) +
  geom_line() +
  facet_wrap(~ period, scales = "free_x") +
  labs(
    title = "Stablecoin transfer volume by period",
    x = "Time",
    y = "Transfer volume, USD"
  ) +
  theme_minimal()

ggsave(
  file.path(results_dir, "volume_by_period.png"),
  p2,
  width = 10,
  height = 5,
  dpi = 300
)

cat("\nTwo-period analysis complete. Results saved to:\n")
cat(results_dir, "\n")