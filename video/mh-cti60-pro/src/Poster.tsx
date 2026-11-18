import { defineComponent, field, Instance, Layer, basicTransformParameters, basicTransformValue, Graphic, basicGraphicPresets, defineContainerComponent } from '@motionharness/sdk';
import { Title } from './Title';

const GraphicGroup = defineContainerComponent({ id: 'graphic-group', component: Graphic, presets: basicGraphicPresets });

export const Poster = defineComponent({
  id: 'poster',
  parameters: {
    ...basicTransformParameters(),
    background: field.color({ label: '画布背景', labelTranslations: { en: 'Canvas background' }, default: '#111827', animatable: true }),
    graphics: field.componentList({ label: '基础图形', component: Graphic, presets: basicGraphicPresets }),
    groups: field.componentList({ label: '容器', component: GraphicGroup }),
    main: field.component({ label: '主标题', component: Title, initialProps: { text: '新品发布', fontSize: 64 } }),
    subtitle: field.component({ label: '副标题', component: Title, editableTiming: true, initialProps: { text: '让创意动起来', fontSize: 32 } }),
  },
  component(values) {
    const {main,subtitle,graphics,groups,background}=values;
    return <Layer bindings="parameters" value={basicTransformValue(values)} style={{ position: 'relative', width: '100%', height: '100%', display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', gap: 24, background }}>
      <Instance value={main} /><Instance value={subtitle} />
      {graphics.map(item => <Instance key={item.$instance} value={item} />)}
      {groups.map(item => <Instance key={item.$instance} value={item} />)}
    </Layer>;
  },
});
