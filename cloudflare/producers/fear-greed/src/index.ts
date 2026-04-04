const JSON_HEADERS = {
  "content-type": "application/json; charset=utf-8",
  "cache-control": "no-store",
};

export default {
  async fetch(): Promise<Response> {
    return new Response(
      JSON.stringify(
        {
          worker: "fear-greed-producer",
          role: "scheduled-producer",
          status: "ok",
          message: "This worker runs on cron triggers and refreshes fear-greed artifacts via scripts/cloudflare_refresh_app.sh fear-greed.",
        },
        null,
        2,
      ),
      { headers: JSON_HEADERS },
    );
  },
  async scheduled(controller: ScheduledController): Promise<void> {
    console.log("fear-greed-producer placeholder", controller.cron);
  },
};
