import { PaymentProcessor } from './PaymentProcessor';
export class PaymentProcessorV2 {
  private inner = new PaymentProcessor();
  process(amount: number): string { return this.inner.process(amount, {}); }
}
