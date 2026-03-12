Component({
  data: {
    gpaDisplay: '--',
  },
  properties: {
    gpa: {
      type: Number,
      value: 0,
      observer(value: number) {
        const numeric = Number(value)
        this.setData({
          gpaDisplay: numeric > 0 ? numeric.toFixed(2) : '--',
        })
      },
    },
    totalCredits: { type: Number, value: 0 },
    passedCredits: { type: Number, value: 0 },
    failedCount: { type: Number, value: 0 },
  },
})
