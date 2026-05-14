import { greeting } from '../../shared/src/utils';
export class ApiServer {
  start(): void { console.log(greeting('api')); }
}
