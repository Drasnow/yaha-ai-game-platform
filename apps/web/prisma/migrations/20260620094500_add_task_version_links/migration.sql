-- AlterTable
ALTER TABLE "game_versions" ADD COLUMN "result_task_id" TEXT;

-- CreateIndex
CREATE UNIQUE INDEX "game_versions_result_task_id_key" ON "game_versions"("result_task_id");

-- CreateIndex
CREATE UNIQUE INDEX "generation_tasks_result_version_id_key" ON "generation_tasks"("result_version_id");

-- AddForeignKey
ALTER TABLE "game_versions" ADD CONSTRAINT "game_versions_result_task_id_fkey" FOREIGN KEY ("result_task_id") REFERENCES "generation_tasks"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "generation_tasks" ADD CONSTRAINT "generation_tasks_result_version_id_fkey" FOREIGN KEY ("result_version_id") REFERENCES "game_versions"("id") ON DELETE SET NULL ON UPDATE CASCADE;
