FROM trufflesuite/ganache:v7.9.2
USER root
RUN mkdir -p /data/chain
ENTRYPOINT ["node", "/app/dist/node/cli.js"]
CMD ["--server.host", "::", "--server.port", "8545", "--chain.chainId", "1337", "--database.dbPath", "/data/chain", "--logging.quiet", "true"]
