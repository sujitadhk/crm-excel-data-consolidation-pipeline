# Data Quality Report

## Cleaning summary

- **Raw Crm Rows**: 315
- **Raw Sales Rows**: 1700
- **Duplicates Removed**: 15
- **Invalid Quantity Rows**: 22
- **Orphan Customer Rows**: 26
- **Unknown Sku Rows**: 0
- **Duplicate Order Ids**: 0
- **Clean Customers**: 300
- **Clean Sales Rows**: 1652
- **Total Revenue**: 2335704.01

## Validation checks

| Check | Status |
|---|---|
| Unique customer_id | PASS |
| Unique order_id | PASS |
| No negative revenue | PASS |
| No missing order dates | PASS |
| All countries standardised | PASS |
| Warehouse revenue reconciles to source | PASS |