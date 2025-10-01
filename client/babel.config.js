module.exports = {
  presets: [
    ['@babel/preset-env', {
      useBuiltIns: 'usage',
      corejs: 3,
      targets: {
        browsers: ['> 1%', 'last 2 versions']
      }
    }],
    ['@babel/preset-react', {
      runtime: 'automatic'
    }]
  ]
};
