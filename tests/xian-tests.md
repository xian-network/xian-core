Xian Tests

Motivation : 

All tests should run in a standardised environment, where all variables are controlled & predictable.

- `.cometbft` to be a fixture in tests which is copied to a tmp directory at start of each test
    - should be a 'vanilla', blank state, necessary state for tests is to be added to the tmp state at the beginning of each test as needed.
- xian.constants to be overridden with test values.