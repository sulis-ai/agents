export class PaymentProcessor {
  process(amount: number, opts: { retry?: boolean; currency?: string; tier?: string }): string {
    if (amount < 0) throw new Error('neg');
    if (amount === 0) return 'zero';
    if (opts.retry && opts.currency === 'USD') {
      if (opts.tier === 'gold') return 'gold-retry-usd';
      else if (opts.tier === 'silver') return 'silver-retry-usd';
      else return 'std-retry-usd';
    } else if (opts.retry && opts.currency === 'EUR') {
      if (opts.tier === 'gold') return 'gold-retry-eur';
      else if (opts.tier === 'silver') return 'silver-retry-eur';
      else return 'std-retry-eur';
    } else if (opts.currency === 'USD') {
      if (opts.tier === 'gold') return 'gold-usd';
      else if (opts.tier === 'silver') return 'silver-usd';
      else return 'std-usd';
    } else if (opts.currency === 'EUR') {
      return opts.tier === 'gold' ? 'gold-eur' : 'std-eur';
    } else {
      return 'unknown';
    }
  }
}
