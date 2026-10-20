# Azure cost and resources

## Pay-as-you-go has no spending limit · step 0.3

Azure's spending limit exists only on credit-based subscriptions (free trial, Students, Visual Studio). On pay-as-you-go nothing stops spending automatically, and budgets only send alerts, with several hours of lag. Real protection needs automation that acts: the automatic cost stop and nightly teardown planned in step 3.7. Model tokens are billed outside Azure and are capped by prepaid credits instead.

## Test the alert path · step 0.3

Budgets can't be triggered on demand, but the action group they notify can. The test failed with "no valid receivers" until the email address was verified. Without the test, the first real budget alert would have gone nowhere.

## Choosing a region by feature availability · step 0.3

Preview services roll out region by region. East US 2 was chosen because Content Safety Task Adherence and the APIM AI Gateway tier are not available in India regions. The latency cost (about 200–250 ms) doesn't matter for this workload.

## Soft delete, purge protection and name suffixes · step 0.3

A deleted Key Vault is recoverable for 90 days and, with purge protection, cannot be purged early, so a deleted name stays taken. Storage account and vault names are global (they become public URLs), so a random suffix keeps them unique and avoids clashes with soft-deleted leftovers.
