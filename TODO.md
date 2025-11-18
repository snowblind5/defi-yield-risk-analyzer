# DeFi Yield Risk Analyzer - TODO

## Phase 1: Core Infrastructure ✓
- [x] Define project structure
- [x] Create requirements.txt
- [x] Create configuration file
- [ ] Complete database models
- [ ] Build data collector
- [ ] Build risk calculator
- [ ] Create update scripts

## Phase 2: Risk Scoring (To Be Refined)
- [ ] **Validate risk weight assumptions**
  - Current: APY volatility (30%), TVL volatility (30%), Liquidity (40%)
  - Consider: Should protocol age/audits be included?
  - Consider: Should impermanent loss risk be weighted differently?
  
- [ ] **Define risk score calculation methodology**
  - How to normalize APY volatility across different pool types?
  - Should stablecoin pools have different thresholds?
  - How to handle new pools with limited history?
  
- [ ] **Calibrate risk thresholds**
  - Current: Low (0-30), Medium (30-60), High (60-100)
  - Validate against real DeFi incidents/losses
  - Research industry standards for risk classification

- [ ] **Additional risk factors to consider**
  - Smart contract audit status (if data available)
  - Protocol age/maturity
  - Historical exploit/hack events
  - Concentration risk (single token exposure)
  - Impermanent loss magnitude for LP positions

## Phase 3: Dashboard Development
- [ ] Design dashboard layout (wireframe)
- [ ] Implement main overview page
- [ ] Implement pool explorer with filters
- [ ] Implement risk analysis visualizations
- [ ] Implement historical trends charts
- [ ] Add export functionality

## Phase 4: CI/CD & Deployment
- [ ] Write GitHub Actions workflow
- [ ] Test automated data updates
- [ ] Deploy to Streamlit Cloud
- [ ] Set up monitoring/alerts for failures

## Phase 5: Documentation & Polish
- [ ] Write comprehensive README
- [ ] Add architecture diagram
- [ ] Document risk methodology
- [ ] Create demo video
- [ ] Add code comments
- [ ] Write unit tests (optional but good)

## Research Questions
- [ ] What are industry-standard risk metrics for DeFi?
- [ ] How do professional DeFi funds evaluate opportunities?
- [ ] What risk-adjusted return metrics are most relevant?
- [ ] Should we include correlation analysis across pools?

## Future Enhancements (Post-MVP)
- [ ] Portfolio simulation tool
- [ ] Email/Telegram alerts for risk changes
- [ ] Historical backtest of strategies
- [ ] Integration with on-chain data (The Graph)
- [ ] Multi-chain portfolio tracking
- [ ] User authentication for saved portfolios