with open('d:/ccf/frontend/src/app/evangelism/faro/groups/page.tsx', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Remove <> and </>
content = content.replace(
    '<>\n          <div className="flex-1 bg-white dark:bg-[#252528]',
    '<div className="flex-1 bg-white dark:bg-[#252528]'
)
content = content.replace(
    '          </div>\n          </>\n        ) : (',
    '          </div>\n        ) : ('
)

# 2. Add the {mode === 'crear' || mode === 'editar' ? ( before the form container
content = content.replace(
    '            <div className="flex-1 overflow-y-auto px-8 py-6 scrollbar-thin">\n              {!isCreating && (',
    '            {mode === \'crear\' || mode === \'editar\' ? (\n              <div className="flex-1 overflow-y-auto px-8 py-6 scrollbar-thin">\n                {!isCreating && ('
)

# 3. Replace the transition between the form container and the members container
# From:
#             </div>
#           </div>
#           <div className="flex-1 overflow-y-auto bg-white dark:bg-[#1e1f21]">
# To:
#               </div>
#             ) : (
#               <div className="flex-1 overflow-y-auto bg-white dark:bg-[#1e1f21]">
content = content.replace(
    '            </div>\n          </div>\n          <div className="flex-1 overflow-y-auto bg-white dark:bg-[#1e1f21]">',
    '              </div>\n            ) : (\n              <div className="flex-1 overflow-y-auto bg-white dark:bg-[#1e1f21]">'
)

# 4. Close the ternary operator at the end
content = content.replace(
    '              </div>\n            )}\n          </div>\n        ) : (',
    '              </div>\n            )}\n              </div>\n            )}\n        ) : ('
)

with open('d:/ccf/frontend/src/app/evangelism/faro/groups/page.tsx', 'w', encoding='utf-8') as f:
    f.write(content)

print("Fix applied")
