module.exports = {
    testEnvironment: 'jsdom',
    moduleFileExtensions: ['js'],
    testMatch: ['**/tests/js/**/*.test.js'],
    // Transform ES modules for Jest
    transform: {},
    // Handle ES module imports
    moduleNameMapper: {
        '^(\\.{1,2}/.*)\\.js$': '$1',
    },
    // Setup files to run before tests
    setupFilesAfterEnv: ['<rootDir>/tests/js/setup.js'],
    // Collect coverage from static/js files
    collectCoverageFrom: [
        'app/static/js/**/*.js',
        '!app/static/js/dashboard.js', // Exclude the old monolithic file
    ],
    coverageDirectory: 'coverage',
};
