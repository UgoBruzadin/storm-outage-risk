# The dashboard as a container: `docker compose up`, then open http://localhost:8501
#
# Two stages: the first uses pixi to install the minimal "app" environment
# from the lock file (exact versions, same as on your laptop); the second
# copies only that environment + the app code into a slim image — no pixi,
# no dbt, no ML libraries, no raw data.
#
# Data: by default the image bundles data/app/ (run `pixi run export-app`
# before building). To read the published Hugging Face dataset instead, set
# APP_DATA=hf://datasets/<user>/<dataset> at run time.

FROM ghcr.io/prefix-dev/pixi:0.53.0 AS build
WORKDIR /app
COPY pixi.toml pixi.lock ./
RUN pixi install --locked -e app
# a script that activates the environment, then runs the container's command
RUN pixi shell-hook -e app -s bash > /shell-hook.sh && echo 'exec "$@"' >> /shell-hook.sh

FROM ubuntu:24.04
WORKDIR /app
COPY --from=build /app/.pixi/envs/app /app/.pixi/envs/app
COPY --from=build /shell-hook.sh /shell-hook.sh
COPY app/ app/
COPY .streamlit/ .streamlit/
COPY data/app/ data/app/

ENV PORT=8501 \
    APP_DATA=/app/data/app
EXPOSE 8501
# run as a non-root user
RUN useradd --create-home appuser && chown -R appuser /app
USER appuser

ENTRYPOINT ["/bin/bash", "/shell-hook.sh"]
# --server.address=0.0.0.0: reachable from outside the container (the local
# config.toml says localhost, which only makes sense outside Docker)
CMD ["sh", "-c", "streamlit run app/streamlit_app.py --server.address=0.0.0.0 --server.port=${PORT}"]
