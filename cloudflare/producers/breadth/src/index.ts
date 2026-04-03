const JSON_HEADERS = {
  "content-type": "application/json; charset=utf-8",
  "cache-control": "no-store",
};

export default {
  async fetch(): Promise<Response> {
    return new Response(
      JSON.stringify(
        {
          worker: "breadth-producer",
          role: "scheduled-producer",
          status: "ok",
          message: "This worker runs on cron triggers and is not a public app endpoint.",
          schedules: ["30 6 * * 2-6", "0 8 * * 2-6"],
        },
        null,
        2,
      ),
      { headers: JSON_HEADERS },
    );
  },
  async scheduled(controller: ScheduledController): Promise<void> {
    console.log("breadth-producer placeholder", controller.cron);
  },
};
