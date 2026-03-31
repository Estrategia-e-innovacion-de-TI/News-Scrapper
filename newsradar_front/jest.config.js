const config = {
  preset: 'jest-preset-angular',
  setupFilesAfterEnv: ['<rootDir>/setup-jest.ts'],
  testEnvironment: 'jsdom',
  watchPlugins: [
    'jest-watch-typeahead/filename',
    'jest-watch-typeahead/testname',
  ],
  transform: {
    '^.+\\.(ts|mjs|js|html|svg)$': [
      'jest-preset-angular',
      {
        tsconfig: '<rootDir>/tsconfig.spec.json',
        stringifyContentPathRegex: '\\.(html|svg)$',
      },
    ],
  },
  transformIgnorePatterns: [
    'node_modules/(?!(@angular|d3|d3-.*|delaunator|internmap|robust-predicates|rxjs|tslib|zone.js)/)',
  ],
  testPathIgnorePatterns: [
    '<rootDir>/node_modules/',
    '<rootDir>/dist/',
    '<rootDir>/tests/',
    '<rootDir>/src/main.ts',
    '<rootDir>/src/app/config/environment.ts',
    '<rootDir>/src/app/config/environment.prod.ts',
  ],
  coverageDirectory: '<rootDir>/coverage/',
  coverageReporters: ['html', 'json', 'text', 'lcov', 'cobertura'],
  collectCoverageFrom: [
    'src/**/*.ts',
    '!src/main.ts',
    '!src/main.server.ts',
    '!src/server.ts',
    '!src/app/config/environment.ts',
    '!src/app/config/environment.prod.ts',
  ],
  coverageThreshold: {
    global: {
      statements: 80,
      branches: 80,
      functions: 80,
      lines: 80,
    },
  },
  reporters: [
    'default',
    ['jest-junit', { outputDirectory: './coverage/', outputName: 'junit.xml' }],
    ['jest-html-reporters', { publicPath: './coverage/', filename: 'report-jest.html' }],
    'jest-sonar',
  ],
  moduleFileExtensions: ['ts', 'html', 'js', 'json', 'mjs'],
};

module.exports = config;
