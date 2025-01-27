# Load necessary libraries
library(dplyr)

# Step 1: Read and process daily price data
file_path <- "data/daily_price_ohlc.csv"
daily_price_data <- read.csv(file_path, header = TRUE)

# Process close_df
close_df <- daily_price_data %>%
  select(date_time, open) %>%
  mutate(close = lead(open)) %>%
  filter(!is.na(close)) %>%
  mutate(log_return = log(close / lag(close)))

# Step 2: Read and process daily realized volatility
daily_volatility_df <- read.csv("data/daily_realized_volatility.csv", header = TRUE) %>%
  rename(date_time = date)

# Step 3: Read and process dvol_df
dvol_df <- read.csv("data/dvol_df.csv", header = TRUE)

# Correct the date format in dvol_df
dvol_df <- dvol_df %>%
  mutate(date_time = as.Date(gsub("/", "-", date_time), format = "%Y-%m-%d")) %>%
  mutate(date_time = format(date_time, "%Y-%m-%d"))  # Convert back to character

# Convert annualized implied volatility to daily
dvol_df <- dvol_df %>%
  mutate(iv_daily = close / sqrt(365))  # Convert annualized IV to daily IV

# Process dvol_diff_df
dvol_diff_df <- dvol_df %>%
  select(date_time, close) %>%
  mutate(iv_diff = close - lag(close))

# Step 4: Calculate VRP
vrp_df <- dvol_df %>%
  select(date_time, iv_daily) %>%
  inner_join(daily_volatility_df %>% select(date_time, realized_volatility), by = "date_time") %>%
  mutate(VRP = iv_daily - realized_volatility)

# Step 5: Read and process aggregated Greeks
aggregated_greeks <- read.csv("data/aggregated_greeeks.csv", header = TRUE) %>%
  rename(date_time = date_only)

# Step 6: Select relevant columns for final join
close_df_selected <- close_df %>%
  select(date_time, log_return)

dvol_diff_df_selected <- dvol_diff_df %>%
  select(date_time, iv_diff)

vrp_df_selected <- vrp_df %>%
  select(date_time, VRP)

aggregated_greeks_selected <- aggregated_greeks %>%
  select(date_time, Delta, Gamma, Vega)

# Step 7: Perform final join operations
final_df <- close_df_selected %>%
  left_join(dvol_diff_df_selected, by = "date_time") %>%
  left_join(vrp_df_selected, by = "date_time") %>%
  left_join(aggregated_greeks_selected, by = "date_time")

# Step 8: Drop rows with NA values
final_df <- final_df %>%
  filter(complete.cases(.))

# View the final DataFrame
head(final_df)


if (!requireNamespace("tseries", quietly = TRUE)) {
  install.packages("tseries")
}
if (!requireNamespace("urca", quietly = TRUE)) {
  install.packages("urca")
}

# Load the libraries
library(tseries)
library(urca)

# Define a function to perform ADF, PP, and DF-GLS tests
perform_stationarity_tests <- function(series, series_name) {
  # Ensure the series is clean and numeric
  series <- na.omit(series)
  series <- as.numeric(series)
  
  # ADF Test using urca for critical values
  adf_test <- ur.df(series, type = "drift", selectlags = "AIC")
  adf_stat <- adf_test@teststat[1]
  adf_crit_value <- adf_test@cval[1, "5pct"]
  adf_p_value <- ifelse(adf_stat < adf_crit_value, "< 0.05", "> 0.05")  # Approximate p-value
  
  # PP Test
  pp_test <- pp.test(series)
  pp_stat <- pp_test$statistic
  pp_p_value <- pp_test$p.value
  # Note: pp.test() does not provide critical values directly; add "N/A" for PP critical value
  pp_crit_value <- "N/A"
  
  # DF-GLS Test
  dfgls_test <- ur.ers(series, type = "DF-GLS", model = "constant", lag.max = 4)
  dfgls_stat <- dfgls_test@teststat
  dfgls_crit_value <- dfgls_test@cval["5pct"]
  dfgls_p_value <- ifelse(dfgls_stat < dfgls_crit_value, "< 0.05", "> 0.05")  # Approximate p-value
  
  # Print test results
  cat("Stationarity Test Results for", series_name, ":\n")
  cat("ADF Test: Test Statistic =", adf_stat, "(Critical Value =", adf_crit_value, "), Approximate p-value =", adf_p_value, "\n")
  cat("PP Test: Test Statistic =", pp_stat, "(Critical Value =", pp_crit_value, "), p-value =", pp_p_value, "\n")
  cat("DF-GLS Test: Test Statistic =", dfgls_stat, "(Critical Value =", dfgls_crit_value, "), Approximate p-value =", dfgls_p_value, "\n\n")
  
  # Return results as a data frame
  return(data.frame(
    Series = series_name,
    ADF = paste0(round(adf_stat, 4), " (", round(adf_crit_value, 4), ")"),
    ADF_p_value = adf_p_value,
    PP = paste0(round(pp_stat, 4), " (", pp_crit_value, ")"),
    PP_p_value = round(pp_p_value, 4),
    DF_GLS = paste0(round(dfgls_stat, 4), " (", round(dfgls_crit_value, 4), ")"),
    DF_GLS_p_value = dfgls_p_value
  ))
}

# Variables to test
variables_to_test <- c("log_return", "iv_diff", "VRP", "Delta", "Gamma", "Vega")

# Initialize result storage
results_list <- list()

# Perform stationarity tests on each variable
for (var in variables_to_test) {
  series <- final_df[[var]]
  test_result <- perform_stationarity_tests(series, var)
  results_list[[var]] <- test_result
}

# Combine all results
all_results <- do.call(rbind, results_list)

# Save results to a CSV file
write.csv(all_results, "stationarity_tests_results.csv", row.names = FALSE)


## Build VAR(1) model
if (!requireNamespace("vars", quietly = TRUE)) {
  install.packages("vars")
}
library(vars)


var_data <- final_df[, c("log_return", "iv_diff", "VRP", "Delta", "Gamma", "Vega")]
var_model <- VAR(var_data, p = 1, type = "const") # Fit the VAR(1) model
summary(var_model)

# Check the stability of the VAR model
stability_results <- stability(var_model)

# Plot the stability results
plot(stability_results)

# Compute the roots of the VAR model
roots <- roots(var_model)
cat("Roots of the VAR model:\n", roots, "\n")

# Plot the real and imaginary parts of the roots
plot(Re(roots), Im(roots), xlim = c(-1.5, 1.5), ylim = c(-1.5, 1.5),
     xlab = "Real Part", ylab = "Imaginary Part",
     main = "Roots of VAR(1) Model", pch = 19, asp = 1)
# Add the unit circle
symbols(0, 0, circles = 1, inches = FALSE, add = TRUE, fg = "blue")
abline(h = 0, v = 0, col = "gray", lty = 2)



