"use client";
import { Card } from "@xuliu/ui";
import { ArrowRight, CircleHelp } from "lucide-react";
import Link from "next/link";

import { PageHeader } from "../page-shared";
export function HelpPage() {
  return (
    <>
      <PageHeader
        eyebrow="A LITTLE GUIDANCE"
        title="从第一篇内容，到持续创作"
        description="这份指南只描述当前开发版中可以实际操作的功能。"
      />
      <div className="help-grid">
        {[
          [
            "01",
            "告诉创作者，什么是真的",
            "在品牌与事实库中填写真实产品信息、功能及出处。核实后再用于内容。",
            "/brand",
            "添加品牌资料",
          ],
          [
            "02",
            "设定你的创作节奏",
            "建立创作者，选择平台内容规格、时区、创作日和预算。点击“准备今日内容”生成草稿。",
            "/creator",
            "设置创作者",
          ],
          [
            "03",
            "把内容调整到你满意",
            "在内容工作室编辑标题与正文，检查预审提醒。人工复核后准备真实 ZIP 包。",
            "/campaigns",
            "打开内容工作室",
          ],
          [
            "04",
            "让产品故事动起来",
            "上传授权截图或录屏，使用 MG 与素材引擎，创建镜头工程，后台渲染真实 1080p MP4。",
            "/studio/video/new",
            "制作宣传视频",
          ],
          [
            "05",
            "最后的发布，由你完成",
            "下载素材、复制文案，在官方平台自行上传并发布，回到软件填写检查表并登记。",
            "/publish",
            "打开人工发布中心",
          ],
          [
            "06",
            "让真实数据回流",
            "CSV/XLSX 可匹配字段，也可手工记录指标与作品版本；未知请留空。预览确认后入库，错误批次可撤销。",
            "/analytics/import",
            "导入数据",
          ],
          [
            "07",
            "把反馈变成下一轮实验",
            "标记修改原因、保存主动反馈，再生成证据周报。模型复盘需单独授权并使用预算，策略审批后才影响后续计划，可回滚。",
            "/growth",
            "查看成长与记忆",
          ],
          [
            "08",
            "设置提醒和私有记录",
            "设置站内提醒、模型和价格，导出私有记录；未知费用先核对账单再录入结果。维护页显示实际状态。",
            "/settings",
            "打开设置",
          ],
        ].map(([number, title, desc, href, label]) => (
          <Card key={number}>
            <span className="help-number">{number}</span>
            <h2>{title}</h2>
            <p>{desc}</p>
            <Link className="text-link" href={href}>
              {label}
              <ArrowRight size={14} />
            </Link>
          </Card>
        ))}
      </div>
      <div className="alert">
        <CircleHelp size={18} />
        <span>
          没有模型配置时，输出会标注为本地规则草稿。AI
          预审不能替代平台审核；人工发布结果仅为用户自行登记。
        </span>
      </div>
    </>
  );
}
