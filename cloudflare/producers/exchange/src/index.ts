const JSON_HEADERS = {
  "content-type": "application/json; charset=utf-8",
  "cache-control": "no-store",
};

export default {
  async fetch(): Promise<Response> {
    return new Response(
      JSON.stringify(
        {
          worker: "exchange-producer",
          role: "scheduled-producer",
          status: "ok",
          message:
            "This worker is reserved for cron-driven exchange refresh. Current bridge path is scripts/cloudflare_refresh_app.sh exchange.",
        },
        null,
        2,
      ),
      { headers: JSON_HEADERS },
    );
  },
  async scheduled(controller: ScheduledController): Promise<void> {
    console.log("exchange-producer bridge pending native runtime implementation", controller.cron);
  },
};
