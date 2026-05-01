library(tidyverse)
library(lubridate)

results_dir <- "results_two_periods"

df_2024 <- read_csv("data/processed_2024/dune_stablecoin_cex_hourly.csv") %>%
  mutate(period = "2024 higher-fee period")

df_2026 <- read_csv("data/processed_2026/dune_stablecoin_cex_hourly.csv") %>%
  mutate(period = "2026 low-fee period")

combined <- bind_rows(df_2024, df_2026)

p_gas_density <- ggplot(combined, aes(x = avg_gas_gwei, fill = period)) +
  geom_density(alpha = 0.45) +
  scale_x_log10() +
  labs(
    title = "Distribution of hourly Ethereum gas fees",
    subtitle = "Log scale used because the 2024 period contains extreme gas spikes",
    x = "Average gas fee, Gwei, log scale",
    y = "Density",
    fill = "Period"
  ) +
  theme_minimal()

ggsave(
  file.path(results_dir, "figure1_gas_fee_distribution.png"),
  p_gas_density,
  width = 9,
  height = 5,
  dpi = 300
)

combined <- combined %>%
  mutate(
    time = parse_date_time(
      time,
      orders = c("ymd HMS", "ymd HM", "ymd HMS OS", "ymd HM OS", "ymd"),
      tz = "UTC"
    )
  )

p_gas_time <- ggplot(combined, aes(x = time, y = avg_gas_gwei)) +
  geom_line(linewidth = 0.35) +
  facet_wrap(~ period, scales = "free_x") +
  labs(
    title = "Hourly Ethereum gas fees by period",
    x = "Time",
    y = "Average gas fee, Gwei"
  ) +
  theme_minimal()

ggsave(
  file.path(results_dir, "figure2_gas_fee_time_series.png"),
  p_gas_time,
  width = 10,
  height = 5,
  dpi = 300
)

combined <- combined %>%
  mutate(
    time = parse_date_time(
      time,
      orders = c("ymd HMS", "ymd HM", "ymd HMS OS", "ymd HM OS", "ymd"),
      tz = "UTC"
    )
  )

p_gas_time <- ggplot(combined, aes(x = time, y = avg_gas_gwei)) +
  geom_line(linewidth = 0.35) +
  facet_wrap(~ period, scales = "free_x") +
  labs(
    title = "Hourly Ethereum gas fees by period",
    x = "Time",
    y = "Average gas fee, Gwei"
  ) +
  theme_minimal()

ggsave(
  file.path(results_dir, "figure2_gas_fee_time_series.png"),
  p_gas_time,
  width = 10,
  height = 5,
  dpi = 300
)

p_scatter <- ggplot(combined, aes(x = log_gas, y = log_volume)) +
  geom_point(alpha = 0.25, size = 1) +
  geom_smooth(method = "lm", se = TRUE) +
  facet_wrap(~ period) +
  labs(
    title = "Gas fees and stablecoin transfer volume",
    x = "Log average gas fee",
    y = "Log stablecoin transfer volume"
  ) +
  theme_minimal()

ggsave(
  file.path(results_dir, "figure3_gas_volume_relationship.png"),
  p_scatter,
  width = 10,
  height = 5,
  dpi = 300
)

shock_effects <- tibble(
  period = c("2024 higher-fee period", "2026 low-fee period"),
  estimate = c(-0.462, -0.462 + 0.797)
)

p_shock <- ggplot(shock_effects, aes(x = period, y = estimate)) +
  geom_col(width = 0.55) +
  geom_hline(yintercept = 0, linetype = "dashed") +
  labs(
    title = "Estimated shock effect by fee regime",
    subtitle = "Effects are from the pooled interaction model; outcome is log transfer volume",
    x = NULL,
    y = "Estimated shock effect"
  ) +
  theme_minimal()

ggsave(
  file.path(results_dir, "figure4_shock_effect_by_period.png"),
  p_shock,
  width = 8,
  height = 5,
  dpi = 300
)