import {
  Canvas, Instance, Layer, defineComponent, defineComposition, field, useInstance, useTime,
  basicTransformParameters, basicTransformValue, basicTransformMatrix,
} from '@motionharness/sdk';
import { drawFilm } from './film';

const SANS = '"Noto Sans TC","Microsoft JhengHei","PingFang TC",sans-serif';
const MONO = '"IBM Plex Mono","Cascadia Mono",ui-monospace,monospace';

/* ---------------- 可編輯：流水線第一張卡片 ---------------- */
const CARD_W = 296, CARD_H = 200;

const PipelineCard = defineComponent({
  id: 'pipeline-card',
  parameters: {
    number: field.text({ label: '序號', default: '01' }),
    heading: field.text({ label: '標題', default: '定時抓取' }),
    sub: field.text({ label: '說明', default: 'iThome・TWCERT/CC・NVD' }),
    fill: field.color({ label: '底色', default: '#131a20', animatable: true }),
    border: field.color({ label: '邊框', default: '#3a4550', animatable: true }),
    ink: field.color({ label: '文字色', default: '#e8ecef', animatable: true }),
    ...basicTransformParameters({
      defaults: { x: 130, y: 520, anchorX: CARD_W / 2, anchorY: CARD_H / 2 },
      animations: {
        y: { keyframes: [{ time: 0, value: 546 }, { time: 0.776, value: 520, easing: 'ease-out' }] },
        opacity: { keyframes: [{ time: 0, value: 0 }, { time: 0.776, value: 1 }, { time: 10.86, value: 1 }, { time: 11.36, value: 0 }, { time: 48, value: 0 }] },
      },
    }),
  },
  component(values) {
    return <Layer bindings="parameters" value={basicTransformValue(values)}
      style={{ position: 'absolute', left: 0, top: 0, width: CARD_W, height: CARD_H }} />;
  },
});

/* ---------------- 可編輯：收尾標題 ---------------- */
const TITLE_W = 1000, TITLE_H = 96;

const EndTitle = defineComponent({
  id: 'end-title',
  parameters: {
    text: field.text({ label: '文字', default: 'CTI 資安風險決策支援平台' }),
    color: field.color({ label: '顏色', default: '#e8ecef', animatable: true }),
    ...basicTransformParameters({
      defaults: { x: 460, y: 432, anchorX: TITLE_W / 2, anchorY: TITLE_H / 2 },
      animations: {
        y: { keyframes: [{ time: 0.78, value: 448 }, { time: 2.12, value: 432, easing: 'ease-out' }] },
        opacity: { keyframes: [{ time: 0, value: 0 }, { time: 1.01, value: 1 }] },
      },
    }),
  },
  component(values) {
    return <Layer bindings="parameters" value={basicTransformValue(values)}
      style={{ position: 'absolute', left: 0, top: 0, width: TITLE_W, height: TITLE_H }} />;
  },
});

/* 卡片在本機像素座標 (0,0)-(296,200) 內繪製，與 Layer 的 anchor 對齊 */
function drawCard(context: CanvasRenderingContext2D, values: any) {
  context.save();
  const matrix = basicTransformMatrix(values);
  context.translate(values.x + values.anchorX, values.y + values.anchorY);
  context.transform(matrix.a, matrix.b, matrix.c, matrix.d, 0, 0);
  context.translate(-values.anchorX, -values.anchorY);
  context.globalAlpha *= values.opacity;

  context.beginPath();
  if (context.roundRect) context.roundRect(0, 0, CARD_W, CARD_H, 10);
  else context.rect(0, 0, CARD_W, CARD_H);
  context.fillStyle = values.fill;
  context.fill();
  context.strokeStyle = values.border;
  context.lineWidth = 1.4;
  context.stroke();

  context.textBaseline = 'alphabetic';
  context.textAlign = 'left';

  context.fillStyle = '#5a6570';
  context.font = '600 20px ' + MONO;
  if ('letterSpacing' in context) (context as any).letterSpacing = '1px';
  context.fillText(values.number, 28, 52);
  if ('letterSpacing' in context) (context as any).letterSpacing = '0px';

  context.fillStyle = values.ink;
  context.font = '600 38px ' + SANS;
  context.fillText(values.heading, 28, 118);

  // 說明文字自動縮到卡片內寬，不再跑出框格
  context.fillStyle = '#8f9aa5';
  const subMax = CARD_W - 56;
  context.font = '500 21px ' + SANS;
  const subW = context.measureText(values.sub).width;
  if (subW > subMax) {
    context.font = '500 ' + (21 * (subMax / subW)).toFixed(1) + 'px ' + SANS;
  }
  context.fillText(values.sub, 28, 164);

  // 步驟圖示：下載箭頭
  const cx = CARD_W - 42, cy = 44;
  context.strokeStyle = '#8f9aa5';
  context.lineWidth = 1.7;
  context.beginPath(); context.moveTo(cx, cy - 11); context.lineTo(cx, cy + 1); context.stroke();
  context.beginPath(); context.moveTo(cx - 6, cy - 5); context.lineTo(cx, cy + 2); context.lineTo(cx + 6, cy - 5); context.stroke();
  context.beginPath(); context.moveTo(cx - 11, cy + 9); context.lineTo(cx + 11, cy + 9); context.stroke();
  context.restore();
}

function drawTitle(context: CanvasRenderingContext2D, values: any, time: number) {
  context.save();
  const matrix = basicTransformMatrix(values);
  context.translate(values.x + values.anchorX, values.y + values.anchorY);
  context.transform(matrix.a, matrix.b, matrix.c, matrix.d, 0, 0);
  // 原片的呼吸縮放（±1.3%，週期約 7.4 秒）留在繪製端，避免與可編輯 transform 衝突
  const localT = 52.9 + (time - 70.50) * (7.1 / 5.5); // scene6 的映射（80 秒版），與 film.ts 一致
  const breathe = 1 + 0.013 * Math.sin((localT - 53.6) * 0.85);
  context.scale(breathe, breathe);
  context.translate(-values.anchorX, -values.anchorY);
  context.globalAlpha *= values.opacity;
  context.fillStyle = values.color;
  context.font = '700 72px ' + SANS;
  context.textAlign = 'center';
  context.textBaseline = 'alphabetic';
  context.fillText(values.text, TITLE_W / 2, TITLE_H / 2, TITLE_W);
  context.restore();
}

const Scene = defineComponent({
  id: 'cti-film',
  parameters: {
    card: field.component({
      label: '流程卡片（定時抓取）',
      component: PipelineCard,
      editableTiming: true,
      timing: { start: 31.31, duration: 48.69 },
    }),
    title: field.component({
      label: '收尾標題',
      component: EndTitle,
      editableTiming: true,
      timing: { start: 70.50 },
    }),
  },
  component({ card, title }) {
    const time = useTime();
    const cardRef = useInstance(card);
    const titleRef = useInstance(title);
    return <div style={{ position: 'relative', width: 1920, height: 1080, overflow: 'hidden' }}>
      <Canvas renderOnly width={1920} height={1080} style={{ position: 'absolute', inset: 0 }}
        draw={({ context }) => {
          drawFilm(context, time, {
            card: { on: cardRef.visible, values: cardRef.values },
            title: { on: titleRef.visible, values: titleRef.values },
          });
          if (cardRef.visible) drawCard(context, cardRef.values);

          if (titleRef.visible) drawTitle(context, titleRef.values, time);
        }} />
      <Instance value={card} />
      <Instance value={title} />
    </div>;
  },
});

export default defineComposition({
  id: 'cti-film',
  component: Scene,
  width: 1920,
  height: 1080,
  fps: 30,
  duration: 76,
});
