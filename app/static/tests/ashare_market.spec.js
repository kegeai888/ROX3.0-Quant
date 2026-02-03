describe('AShareMarket', () => {
  it('normalizes input codes to 6 digits', () => {
    const engine = new AShareMarket(new SimBroker(100000), { autoConnect: false });
    expect(engine._normalizeCode('1')).to.equal('000001');
    expect(engine._normalizeCode('600519')).to.equal('600519');
  });
  it('formats symbol with sh/sz prefix', () => {
    const engine = new AShareMarket(new SimBroker(100000), { autoConnect: false });
    expect(engine._formatSymbol('600519')).to.equal('sh600519');
    expect(engine._formatSymbol('000001')).to.equal('sz000001');
  });
  it('provides cached name for 600519', () => {
    const engine = new AShareMarket(new SimBroker(100000), { autoConnect: false });
    const name = engine.getName('600519');
    expect(name).to.be.a('string');
  });
});
