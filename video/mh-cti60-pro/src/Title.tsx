import { defineComponent, field, Layer, basicTransformParameters, basicTransformValue } from '@motionharness/sdk';
import './title.css';

export const Title = defineComponent({
  id: 'title',
  parameters: {
    text: field.text({ label: '文字', default: '标题' }),
    color: field.color({ label: '颜色', default: '#60a5fa' }),
    fontSize: field.number({ label: '字号', default: 48, min: 12, max: 240, animatable: true }),
    ...basicTransformParameters({ animations: {
      y: { keyframes: [{ time: 0, value: 30, easing: 'ease-out' }, { time: .6, value: 0 }] },
      opacity: { keyframes: [{ time: 0, value: 0, easing: 'ease-out' }, { time: .6, value: 1 }] },
    } }),
  },
  component(values) {
    const { text, color, fontSize } = values;
    return <Layer bindings="parameters" value={basicTransformValue(values)}><h2 className="motion-title" style={{ margin: 0, color, fontSize }}>{text}</h2></Layer>;
  },
});
