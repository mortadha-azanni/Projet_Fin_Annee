module.exports = {
  contextToAppId: ({ securityContext }) => {
    return `CUBEJS_APP_${securityContext?.role || 'default'}`;
  },
  orchestratorOptions: {
    queryCacheOptions: {
      refreshKeyRenewalThreshold: 60,
    },
  },
};
