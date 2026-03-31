import 'jest-preset-angular/setup-env/zone';

import { getTestBed } from '@angular/core/testing';
import {
  BrowserDynamicTestingModule,
  platformBrowserDynamicTesting,
} from '@angular/platform-browser-dynamic/testing';

const testBed = getTestBed();
if (!(globalThis as any).__ANGULAR_TESTBED_INIT__) {
  testBed.initTestEnvironment(
    BrowserDynamicTestingModule,
    platformBrowserDynamicTesting(),
    {
      teardown: { destroyAfterEach: true },
    }
  );
  (globalThis as any).__ANGULAR_TESTBED_INIT__ = true;
}

Object.defineProperty(globalThis, 'crypto', {
  value: {
    subtle: {
      digest: jest.fn(() => Promise.resolve(new ArrayBuffer(32))),
    },
    getRandomValues: (buffer: Uint8Array) => {
      for (let i = 0; i < buffer.length; i++) {
        buffer[i] = Math.floor(Math.random() * 256);
      }
      return buffer;
    },
  },
});
