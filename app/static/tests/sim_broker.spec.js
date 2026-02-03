describe('SimBroker', () => {
  it('applies fees on buy and sell', () => {
    const b = new SimBroker(100000);
    const resBuy = b.executeOrder('600519', 'buy', 100, 100); // amount=10000
    expect(resBuy.success).to.be.true;
    // cash should reduce by amount + fees
    const afterBuyCash = Number(b.account.cash);
    expect(afterBuyCash).to.be.below(90000); // fees deducted
    const resSell = b.executeOrder('600519', 'sell', 100, 100);
    expect(resSell.success).to.be.true;
    // cash should increase by amount - fees
    expect(Number(b.account.cash)).to.be.below(100000); // fees paid on sell
  });
  it('purges zero positions', () => {
    const b = new SimBroker(100000);
    b.executeOrder('000001', 'buy', 10, 10);
    b.executeOrder('000001', 'sell', 10, 10);
    expect(b.account.positions['000001']).to.be.undefined;
    b.purgeZeroPositions(); // noop but should not fail
    expect(b.account.positions['000001']).to.be.undefined;
  });
});
