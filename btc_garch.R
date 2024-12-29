library(rugarch)

setwd("E:/py_projects")
# Prepare sample data: Bitcoin prices
price_data <- read.csv("price_df.csv")
log_returns <- diff(log(price_data$close))

# Specify the GARCH model
for (prior_dist in c("norm","std","ged")){
  spec <- ugarchspec(
    variance.model = list(model = "sGARCH", garchOrder = c(1, 1)),  # GARCH(1,1)
    mean.model = list(armaOrder = c(1, 0), include.mean = TRUE),    # AR(1) in mean model
    distribution.model = prior_dist                                 # distribution
  )
  fit_model<- ugarchfit(spec = spec, data = log_returns)
  print(fit_model)
}


