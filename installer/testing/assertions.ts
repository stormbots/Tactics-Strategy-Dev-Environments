// Keep the maintained assertion implementation; neither this package nor its
// installed distribution includes the removed file-pattern compiler.
import * as chai from "chai";
import {
  JestExtend,
  JestChaiExpect,
  ChaiStyleAssertions,
  JestAsymmetricMatchers,
  GLOBAL_EXPECT,
  ASYMMETRIC_MATCHERS_OBJECT,
  getState,
  setState,
  type ExpectStatic,
} from "@vitest/expect";
chai.use(JestExtend);
chai.use(JestChaiExpect);
chai.use(ChaiStyleAssertions);
chai.use(JestAsymmetricMatchers);
export const expect = ((value: unknown, message?: string) => {
  const state = getState(expect);
  setState({ assertionCalls: state.assertionCalls + 1 }, expect);
  return chai.expect(value, message);
}) as ExpectStatic;
Object.assign(
  expect,
  chai.expect,
  (globalThis as any)[ASYMMETRIC_MATCHERS_OBJECT],
);
expect.getState = () => getState(expect);
expect.setState = (value) => setState(value, expect);
expect.extend = (matchers) => (chai.expect as any).extend(expect, matchers);
setState({ assertionCalls: 0, isExpectingAssertions: false }, expect);
Object.defineProperty(globalThis, GLOBAL_EXPECT, {
  value: expect,
  writable: true,
  configurable: true,
});
