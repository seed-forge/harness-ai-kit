export const name = 'hello-dsh-plugin'
export const inject = ['tools']

export function apply(ctx) {
  ctx.tools.register({
    name: 'hello',
    description: '返回一条问候语。',
    parameters: {
      type: 'object',
      properties: { who: { type: 'string', description: '问候对象' } },
    },
    output: {
      schema: { type: 'object', additionalProperties: true },
      render: (args, value) => [{ type: 'text', text: JSON.stringify(value) }],
    },
    execute: async (args) => ({ ok: true, output: { message: `hello, ${args.who || 'dsh'}` } }),
  })
}
