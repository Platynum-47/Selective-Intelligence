# Selective Inheritance regression — luxury showcase vs wholesaler inventory grammar

When the owner requests a luxury showcase and supplies an existing luxury-oriented website, SI may inherit platform capabilities from a wholesaler implementation, but it must reject that implementation’s inventory-oriented presentation grammar.

## Inherit
- TradeScout: identity, privacy, Direct Connect, sharing, auth, profile ownership
- Owner luxury site: luxury voice, installed-interior imagery, light/install/backlight/custom/consult story, consultation posture
- Wholesaler architecture: stable material IDs + Direct Connect source context only

## Reject
- Owner site public phone/email, testimonials, combined “Honey Green” naming, unsupported specifics
- Wholesaler inventory browser, filters, slab counts, warehouse/yard language, stock badges, product cards, “View details”, catalog navigation

## Linked proof
TradeScoutPro: presentation `luxury-material-house` → `LuxuryMaterialHouseShowcase`; contracts in `issa-build-profile.contract.test.ts` and `PremiumProductProfileSections.test.tsx`.
