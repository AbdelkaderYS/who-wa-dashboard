# analysis.R
# Statistical analysis of WHO health indicators - West Africa (ECOWAS)
# Reads data exported by the Python pipeline (CSV format)
# Produces: correlation analysis, trend modeling, regional summary table
#
# Usage: Rscript analysis.R
# Or: source("analysis.R") in RStudio
# Or: rendered via analysis.Rmd for full report

library(readr)
library(dplyr)
library(tidyr)
library(ggplot2)
library(broom)
library(knitr)

# Showcase trend plot parameters (any country/indicator from the dataset)
TREND_COUNTRY   <- "Niger"
TREND_INDICATOR <- "MDG_0000000007"
TREND_LABEL     <- "Under-five mortality rate (per 1,000 live births)"

# ── Data loading ──────────────────────────────────────────────────────────────

load_who_data <- function(path = "data/who_wa_indicators.csv") {
  if (!file.exists(path)) {
    stop(
      "Data file not found. Run the Python pipeline first:\n",
      "  python pipeline.py --export\n",
      "Expected file: ", path
    )
  }
  df <- read_csv(path, show_col_types = FALSE)
  df$year <- as.integer(df$year)
  df$value <- as.numeric(df$value)
  return(df)
}


# ── Analysis 1: Correlation ───────────────────────────────────────────────────

compute_correlation <- function(df) {
  # Pivot to wide format for correlation between indicators
  # Uses latest available year per country per indicator
  latest <- df %>%
    group_by(country, indicator_code) %>%
    slice_max(year, n = 1) %>%
    ungroup()

  # Aggregate duplicates before pivoting
  latest_agg <- latest %>%
    group_by(country, indicator_code) %>%
    summarise(value = mean(value, na.rm = TRUE), .groups = "drop")

  wide <- latest_agg %>%
    select(country, indicator_code, value) %>%
    pivot_wider(names_from = indicator_code, values_from = value)

  # Force numeric columns
  numeric_cols <- wide %>%
    select(-country) %>%
    mutate(across(everything(), as.numeric))

  # Spearman (rank-based) is the primary method: robust to the extreme values
  # (e.g. Nigeria's absolute counts) that dominate a 15-country sample.
  # Pearson is kept for reference.
  cor_spearman <- cor(numeric_cols, use = "pairwise.complete.obs", method = "spearman")
  cor_pearson  <- cor(numeric_cols, use = "pairwise.complete.obs", method = "pearson")

  return(list(wide = wide, cor_matrix = cor_spearman, cor_pearson = cor_pearson))
}


plot_correlation <- function(cor_matrix, method_label = "Spearman rho") {
  # Convert to long format for ggplot
  cor_df <- as.data.frame(cor_matrix)
  cor_df$indicator_x <- rownames(cor_df)

  cor_long <- cor_df %>%
    pivot_longer(-indicator_x, names_to = "indicator_y", values_to = "correlation")

  ggplot(cor_long, aes(x = indicator_x, y = indicator_y, fill = correlation)) +
    geom_tile(color = "white") +
    geom_text(aes(label = round(correlation, 2)), size = 3, color = "black") +
    scale_fill_gradient2(
      low = "#2166ac", mid = "white", high = "#d73027",
      midpoint = 0, limits = c(-1, 1)
    ) +
    labs(
      title = "Correlation matrix - WHO health indicators",
      subtitle = paste0(
        "West Africa (ECOWAS) - Latest available year per country - ",
        method_label, " (rank-based, robust to extreme values; n = 15 countries)"
      ),
      x = NULL, y = NULL, fill = method_label
    ) +
    theme_minimal(base_size = 12) +
    theme(
      axis.text.x      = element_text(angle = 45, hjust = 1, size = 9),
      axis.text.y      = element_text(size = 9),
      panel.grid       = element_blank(),
      panel.border     = element_blank(),
      plot.title       = element_text(face = "bold", size = 13),
      plot.subtitle    = element_text(color = "gray40", size = 10),
      legend.position  = "right"
    )
}


# ── Analysis 2: Trend modeling ────────────────────────────────────────────────

fit_country_trend <- function(df, country_name, indicator_code_sel) {
  # Filter to one country and one indicator
  ts_data <- df %>%
    filter(country == country_name, indicator_code == indicator_code_sel) %>%
    arrange(year)

  if (nrow(ts_data) < 4) {
    return(NULL)
  }

  # Linear trend model
  model <- lm(value ~ year, data = ts_data)
  model_tidy <- tidy(model)
  model_glance <- glance(model)

  # Fitted values for plot
  ts_data$fitted <- fitted(model)

  list(
    data     = ts_data,
    model    = model,
    tidy     = model_tidy,
    glance   = model_glance,
    slope    = round(coef(model)["year"], 4),
    r2       = round(model_glance$r.squared, 3),
    p_value  = round(model_tidy$p.value[2], 4)
  )
}


plot_trend <- function(trend_result, country_name, indicator_label) {
  if (is.null(trend_result)) {
    message("Insufficient data for trend modeling.")
    return(NULL)
  }

  df_plot <- trend_result$data

  ggplot(df_plot, aes(x = year, y = value)) +
    geom_point(size = 3, color = "#1f77b4") +
    geom_line(color = "#1f77b4", linetype = "dashed", alpha = 0.6) +
    geom_line(aes(y = fitted), color = "#d62728", linewidth = 1) +
    labs(
      title = paste("Trend model -", country_name),
      subtitle = paste0(
        indicator_label,
        " | Slope: ", trend_result$slope,
        " | R2: ", trend_result$r2,
        " | p-value: ", trend_result$p_value
      ),
      x = "Year",
      y = indicator_label
    ) +
    scale_x_continuous(breaks = seq(min(df_plot$year), max(df_plot$year), by = 2)) +
    theme_minimal(base_size = 12) +
    theme(
      panel.grid.minor  = element_blank(),
      panel.grid.major  = element_line(color = "gray90", linewidth = 0.4),
      panel.border      = element_blank(),
      axis.line         = element_line(color = "gray60", linewidth = 0.4),
      plot.title        = element_text(face = "bold", size = 13),
      plot.subtitle     = element_text(color = "gray40", size = 9),
      axis.text         = element_text(size = 10)
    )
}


# ── Analysis 2b: Trend models for ALL country × indicator pairs ──────────────

fit_all_trends <- function(df, min_years = 4) {
  # Linear trend per country per indicator: slope, R2, p-value.
  # Exported for the dashboard so trend inference is not limited to one showcase.
  df %>%
    group_by(country, indicator_code, indicator) %>%
    filter(n() >= min_years) %>%
    group_modify(function(d, key) {
      model <- lm(value ~ year, data = d)
      g <- glance(model)
      t <- tidy(model)
      tibble(
        n_years      = nrow(d),
        period       = paste0(min(d$year), "-", max(d$year)),
        slope_per_yr = round(coef(model)[["year"]], 4),
        r_squared    = round(g$r.squared, 3),
        p_value      = round(t$p.value[2], 4),
        significant  = ifelse(t$p.value[2] < 0.05, "Yes", "No")
      )
    }) %>%
    ungroup() %>%
    arrange(indicator_code, country)
}


# ── Analysis 3: Regional summary table ───────────────────────────────────────

build_regional_table <- function(df) {
  # Latest value + trend direction per country per indicator
  summary_tbl <- df %>%
    group_by(country, indicator_code, indicator) %>%
    arrange(year) %>%
    summarise(
      latest_year  = max(year),
      latest_value = last(value),
      n_years      = n(),
      trend        = if (n() >= 2) {
        slope <- coef(lm(value ~ year))[2]
        case_when(
          slope > 0  ~ "Increasing",
          slope < 0  ~ "Decreasing",
          TRUE       ~ "Stable"
        )
      } else {
        "Insufficient data"
      },
      .groups = "drop"
    ) %>%
    mutate(latest_value = round(latest_value, 2)) %>%
    arrange(indicator_code, country)

  return(summary_tbl)
}


# ── Main execution ────────────────────────────────────────────────────────────

main <- function() {
  cat("Loading WHO West Africa data...\n")
  df <- load_who_data()
  cat("Records loaded:", nrow(df), "\n")
  cat("Countries:", n_distinct(df$country), "\n")
  cat("Indicators:", n_distinct(df$indicator_code), "\n\n")

  # 1. Correlation analysis
  cat("--- Correlation Analysis ---\n")
  cor_result <- compute_correlation(df)
  cat("Correlation matrix (Spearman, primary):\n")
  print(round(cor_result$cor_matrix, 3))
  cat("\nCorrelation matrix (Pearson, reference):\n")
  print(round(cor_result$cor_pearson, 3))

  cor_plot <- plot_correlation(cor_result$cor_matrix)
  ggsave("outputs/correlation_matrix.png", cor_plot, width = 10, height = 8, dpi = 150)
  cat("Saved: outputs/correlation_matrix.png\n\n")

  # 2. Trend models for all country x indicator pairs
  cat("--- Trend Models: all countries x indicators ---\n")
  all_trends <- fit_all_trends(df)
  cat("Models fitted:", nrow(all_trends), "\n")
  write_csv(all_trends, "outputs/trend_models.csv")
  cat("Saved: outputs/trend_models.csv\n\n")

  # 2b. Showcase trend plot (parametrized at top of file)
  cat("--- Trend Model:", TREND_COUNTRY, "-", TREND_LABEL, "---\n")
  trend_showcase <- fit_country_trend(df, TREND_COUNTRY, TREND_INDICATOR)
  if (!is.null(trend_showcase)) {
    cat("Slope:", trend_showcase$slope, "per year\n")
    cat("R2:", trend_showcase$r2, "\n")
    cat("p-value:", trend_showcase$p_value, "\n")
    trend_plot <- plot_trend(trend_showcase, TREND_COUNTRY, TREND_LABEL)
    ggsave("outputs/niger_u5mr_trend.png", trend_plot, width = 9, height = 5, dpi = 150)
    cat("Saved: outputs/niger_u5mr_trend.png\n\n")
  }

  # 3. Regional summary table
  cat("--- Regional Summary Table ---\n")
  regional_tbl <- build_regional_table(df)
  print(regional_tbl)
  write_csv(regional_tbl, "outputs/regional_summary.csv")
  cat("Saved: outputs/regional_summary.csv\n")
}

# Create outputs directory if needed
if (!dir.exists("outputs")) dir.create("outputs")

main()