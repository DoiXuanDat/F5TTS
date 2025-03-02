module.exports = {
  devServer: {
    allowedHosts: 'all',
    proxy: {
      '/api': 'http://localhost:8000'
    },
    headers: {
      'Access-Control-Allow-Origin': '*'
    }
  }
};